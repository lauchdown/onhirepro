frappe.pages['my-rental-calendar'].on_page_load = function(wrapper) {
    frappe.my_rental_calendar_view = new MyRentalCalendarView(wrapper);
}

class MyRentalCalendarView {
    constructor(wrapper) {
        this.wrapper = $(wrapper);
        this.page = wrapper.page;
        this.calendar_events_url = "onhire_pro.onhire_pro.doctype.rental_job.rental_job.get_events"; // Using RentalJob's get_events
        this.make();
    }

    make() {
        this.setup_page_head();
        this.setup_calendar_area();
        this.load_calendar();
    }

    setup_page_head() {
        this.page.set_title(__("My Rental Calendar"));
        // Add any buttons if needed, e.g., refresh
        this.page.add_button(__("Refresh Calendar"), () => {
            this.calendar.refetchEvents();
        }, {icon: "fa fa-refresh"});
    }

    setup_calendar_area() {
        this.wrapper.find(".page-content").append('<div id="customer-rental-calendar" style="margin-bottom: 20px;"></div>');
        this.wrapper.find(".page-content").append(
            `<div class="text-muted small">
                ${__("Note: All event times are displayed in your local timezone.")} 
                (${moment.tz.guess() || 'Unknown Timezone'})
             </div>`
        );
    }

    load_calendar() {
        const calendarEl = document.getElementById('customer-rental-calendar');
        if (!calendarEl) {
            console.error("Calendar element not found.");
            return;
        }

        // Ensure FullCalendar is loaded (Frappe usually includes it)
        if (typeof FullCalendar === 'undefined') {
            frappe.msgprint(__("Calendar library not loaded. Please contact support."));
            return;
        }
        
        this.calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
            },
            events: (fetchInfo, successCallback, failureCallback) => {
                frappe.call({
                    method: this.calendar_events_url,
                    args: {
                        start: fetchInfo.startStr,
                        end: fetchInfo.endStr,
                        // Filters for current customer will be applied by User Permissions on Rental Job
                        // Or, if get_events needs explicit customer, pass it:
                        // customer: frappe.session.user_customer // Assuming this is available
                    },
                    callback: (r) => {
                        if (r.message) {
                            let processed_events = r.message.map(event => {
                                // CP_RENTAL.10.2: Ensure Backend Times are UTC, Display Times in User's Local Timezone
                                // FullCalendar handles timezone conversion if backend provides ISO8601 strings
                                // (which Frappe's get_datetime should do for datetime fields)
                                return {
                                    id: event.name,
                                    title: event.subject || event.name,
                                    start: event.starts_on, // Expecting ISO string e.g. "2023-12-01T10:00:00"
                                    end: event.ends_on,     // Expecting ISO string
                                    allDay: event.all_day || false, // Assuming all_day field if applicable
                                    backgroundColor: event.color || '#3a87ad', // Default color
                                    borderColor: event.color || '#3a87ad',
                                    extendedProps: {
                                        doctype: event.doctype || "Rental Job",
                                        status: event.status
                                    }
                                };
                            });
                            successCallback(processed_events);
                        } else {
                            failureCallback(new Error("Failed to load events"));
                        }
                    },
                    error: () => {
                        failureCallback(new Error("API error fetching events"));
                    }
                });
            },
            eventClick: function(info) {
                // Open the document when an event is clicked
                if (info.event.extendedProps.doctype && info.event.id) {
                    frappe.set_route("Form", info.event.extendedProps.doctype, info.event.id);
                }
            },
            editable: false, // Portal users should not edit events by dragging
            selectable: false,
            dayMaxEvents: true, // when too many events in a day, show the popover
            // CP_RENTAL.10.3: Ensure Mobile Responsiveness of Calendar
            // FullCalendar v5+ is generally responsive. Specific views might need CSS tweaks.
            // The `rental_calendar_mobile.css` can provide further global styling.
            windowResize: (arg) => { // Handle window resize for view changes if needed
                if (arg.view.type === 'listWeek' && window.innerWidth > 768) {
                    // this.calendar.changeView('dayGridMonth'); // Example
                } else if (window.innerWidth <= 768 && arg.view.type !== 'listWeek') {
                    // this.calendar.changeView('listWeek'); // Switch to list view on small screens
                }
            }
        });

        this.calendar.render();
        
        // Initial check for mobile view
        if (window.innerWidth <= 768) {
            this.calendar.changeView('listWeek');
        }
    }
}
