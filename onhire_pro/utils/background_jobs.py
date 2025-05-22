"""
Advanced background job processing system with retries, monitoring, and error handling
"""
import frappe
from frappe.utils.background_jobs import enqueue
from typing import Any, Dict, Optional, Callable, List, Union
import json
import time
from datetime import datetime, timedelta
from .error_handler import log_error, OnHireProError
from .logger import logger

class JobPriority:
    LOW = "low"
    DEFAULT = "default"
    HIGH = "high"
    CRITICAL = "critical"

class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class BackgroundJob:
    def __init__(self, job_id: str, method: str, queue: str, status: str):
        self.job_id = job_id
        self.method = method
        self.queue = queue
        self.status = status
        self.start_time = None
        self.end_time = None
        self.retries = 0
        self.error = None
        self.result = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "method": self.method,
            "queue": self.queue,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "retries": self.retries,
            "error": self.error,
            "result": self.result
        }

class JobManager:
    def __init__(self):
        self.default_timeout = 2000
        self.default_retry_count = 3
        self.retry_delays = [30, 60, 120]  # Exponential backoff
        self.jobs: Dict[str, BackgroundJob] = {}
        
    def enqueue_job(
        self,
        method: Callable,
        queue: str = JobPriority.DEFAULT,
        timeout: int = None,
        event: str = None,
        is_async: bool = True,
        retries: int = None,
        priority: int = 1,
        job_name: str = None,
        at_front: bool = False,
        now: bool = False,
        **kwargs: Any
    ) -> Optional[str]:
        """
        Enhanced job enqueuing with priority, retries, and monitoring
        """
        try:
            timeout = timeout or self.default_timeout
            retries = retries or self.default_retry_count
            
            # Generate unique job name if not provided
            if not job_name:
                job_name = f"{method.__name__}_{frappe.generate_hash(8)}"

            job_data = {
                "method": method.__name__,
                "queue": queue,
                "timeout": timeout,
                "kwargs": kwargs,
                "retry_count": retries,
                "priority": priority,
                "job_name": job_name
            }
            
            # Wrap the method with retry and monitoring
            wrapped_method = self._wrap_method(method, job_data)
            
            # Add job to queue
            job = enqueue(
                wrapped_method,
                queue=queue,
                timeout=timeout,
                event=event,
                is_async=is_async,
                job_name=job_name,
                at_front=at_front,
                **kwargs
            )
            
            # Track job
            background_job = BackgroundJob(
                job_id=job.id,
                method=method.__name__,
                queue=queue,
                status=JobStatus.QUEUED
            )
            self.jobs[job.id] = background_job
            
            # Track job in database
            self._track_job(job.id, job_data)
            
            return job.id
            
        except Exception as e:
            log_error(e, "Background Job Error")
            raise OnHireProError("Failed to enqueue job", {"error": str(e)})
    
    def _wrap_method(self, method: Callable, job_data: Dict[str, Any]) -> Callable:
        """Wrap method with retry and monitoring logic"""
        @wraps(method)
        def wrapper(*args, **kwargs):
            job_id = frappe.get_doc("Background Job").name
            retries = job_data["retry_count"]
            
            for attempt in range(retries + 1):
                try:
                    # Update job status
                    self._update_job_status(job_id, JobStatus.RUNNING)
                    
                    # Execute method
                    result = method(*args, **kwargs)
                    
                    # Update successful completion
                    self._update_job_status(
                        job_id,
                        JobStatus.COMPLETED,
                        result=result
                    )
                    
                    return result
                    
                except Exception as e:
                    if attempt < retries:
                        # Log retry attempt
                        logger.warning(
                            f"Job {job_id} failed, attempt {attempt + 1}/{retries}",
                            extra={"error": str(e)}
                        )
                        
                        # Update retry status
                        self._update_job_status(
                            job_id,
                            JobStatus.RETRYING,
                            error=str(e)
                        )
                        
                        # Wait before retry with exponential backoff
                        delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                        time.sleep(delay)
                    else:
                        # Final failure
                        self._update_job_status(
                            job_id,
                            JobStatus.FAILED,
                            error=str(e)
                        )
                        raise
            
        return wrapper
    
    def _track_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Track job in database with enhanced metadata"""
        frappe.get_doc({
            "doctype": "Background Job",
            "job_id": job_id,
            "status": JobStatus.QUEUED,
            "job_data": json.dumps(job_data),
            "creation": frappe.utils.now(),
            "priority": job_data.get("priority", 1),
            "queue": job_data.get("queue", JobPriority.DEFAULT),
            "method": job_data.get("method"),
            "job_name": job_data.get("job_name")
        }).insert(ignore_permissions=True)
    
    def _update_job_status(
        self,
        job_id: str,
        status: str,
        result: Any = None,
        error: str = None
    ) -> None:
        """Update job status with enhanced tracking"""
        try:
            job = frappe.get_doc("Background Job", {"job_id": job_id})
            job.status = status
            
            if status == JobStatus.RUNNING:
                job.start_time = frappe.utils.now()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.end_time = frappe.utils.now()
                
            if result:
                job.result = json.dumps(result)
            if error:
                job.error = error
                job.retries += 1
                
            job.save(ignore_permissions=True)
            
            # Update in-memory tracking
            if job_id in self.jobs:
                self.jobs[job_id].status = status
                self.jobs[job_id].end_time = job.end_time
                self.jobs[job_id].result = result
                self.jobs[job_id].error = error
                
        except Exception as e:
            logger.error(f"Failed to update job status: {str(e)}")

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get detailed job status"""
        try:
            job = frappe.get_doc("Background Job", {"job_id": job_id})
            return {
                "status": job.status,
                "start_time": job.start_time,
                "end_time": job.end_time,
                "retries": job.retries,
                "error": job.error,
                "result": json.loads(job.result) if job.result else None
            }
        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}")
            return {"status": "unknown", "error": str(e)}

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or queued job"""
        try:
            job = frappe.get_doc("Background Job", {"job_id": job_id})
            if job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                job.status = JobStatus.CANCELLED
                job.end_time = frappe.utils.now()
                job.save(ignore_permissions=True)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cancel job: {str(e)}")
            return False

    def cleanup_old_jobs(self, days: int = 7) -> None:
        """Clean up old completed jobs"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            frappe.db.delete(
                "Background Job",
                {
                    "creation": ("<=", cutoff_date),
                    "status": ("in", [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED])
                }
            )
            frappe.db.commit()
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {str(e)}")

# Initialize global job manager
job_manager = JobManager()

# Example background tasks
def process_rental_returns() -> None:
    """Process rental returns in background with enhanced error handling"""
    try:
        # Get overdue rentals
        overdue_rentals = frappe.get_all(
            "Rental Order",
            filters={
                "status": "Active",
                "end_date": ("<", frappe.utils.now())
            }
        )
        
        for rental in overdue_rentals:
            job_manager.enqueue_job(
                process_single_return,
                queue=JobPriority.HIGH,
                rental_id=rental.name,
                priority=2,
                job_name=f"return_processing_{rental.name}"
            )
    except Exception as e:
        log_error(e, "Rental Return Processing Error")
        raise OnHireProError("Failed to process rental returns", {"error": str(e)})

def process_single_return(rental_id: str) -> Dict[str, Any]:
    """Process single rental return with enhanced tracking"""
    try:
        rental_doc = frappe.get_doc("Rental Order", rental_id)
        
        # Process return logic
        rental_doc.status = "Returned"
        rental_doc.return_date = frappe.utils.now()
        rental_doc.save()
        
        # Return success response
        return {
            "success": True,
            "rental_id": rental_id,
            "return_date": rental_doc.return_date
        }
        
    except Exception as e:
        log_error(e, f"Return Processing Error: {rental_id}")
        raise OnHireProError(
            "Failed to process rental return",
            {"rental_id": rental_id, "error": str(e)}
        )

def schedule_background_jobs() -> None:
    """Schedule recurring background jobs with enhanced monitoring"""
    try:
        # Schedule rental returns processing
        job_manager.enqueue_job(
            process_rental_returns,
            queue=JobPriority.HIGH,
            is_async=True,
            event='daily_long',
            job_name="daily_rental_returns"
        )
        
        # Schedule old job cleanup
        job_manager.enqueue_job(
            job_manager.cleanup_old_jobs,
            queue=JobPriority.LOW,
            is_async=True,
            event='daily',
            job_name="cleanup_old_jobs"
        )
        
    except Exception as e:
        log_error(e, "Job Scheduling Error")
        raise OnHireProError("Failed to schedule background jobs", {"error": str(e)})
