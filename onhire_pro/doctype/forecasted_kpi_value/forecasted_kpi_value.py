# Project/onhire_pro/onhire_pro/doctype/forecasted_kpi_value/forecasted_kpi_value.py
import frappe
from frappe.model.document import Document

class ForecastedKPIValue(Document):
    def autoname(self):
        # Naming: FKV-KPI Name-Forecast Date
        self.name = f"FKV-{self.kpi_name}-{self.forecast_date}"

    def validate(self):
        if not self.kpi_name or not self.forecast_date:
            frappe.throw("KPI Name and Forecast Date are mandatory.")
        
        # Ensure unique combination of kpi_name, forecast_date, periodicity, and company
        # to avoid duplicate forecast entries for the same point.
        existing = frappe.db.exists("Forecasted KPI Value", {
            "kpi_name": self.kpi_name,
            "forecast_date": self.forecast_date,
            "periodicity": self.periodicity,
            "company": self.company,
            "name": ["!=", self.name] # Exclude current doc if updating
        })
        if existing:
            frappe.throw(f"A forecast for KPI '{self.kpi_name}' on date '{self.forecast_date}' with periodicity '{self.periodicity}' for company '{self.company}' already exists: {existing}")
