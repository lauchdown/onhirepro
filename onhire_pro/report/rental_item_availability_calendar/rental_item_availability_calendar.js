// Project/onhire_pro/onhire_pro/report/rental_item_availability_calendar/rental_item_availability_calendar.js
frappe.query_reports["Rental Item Availability Calendar"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_days(frappe.datetime.now_date(), 30),
            "reqd": 1
        },
        {
            "fieldname": "item_code",
            "label": __("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "get_query": function() {
                return { filters: { "is_rental_item": 1 } }
            }
        },
        {
            "fieldname": "item_group",
            "label": __("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group"
        },
        {
            "fieldname": "status",
            "label": __("Event Type"),
            "fieldtype": "Select",
            "options": "\nRental Job\nMaintenance Task", // Add more if needed
            "default": "Rental Job"
        }
    ],
    "formatter": function(value, row, column, data, Rreport) {
        if (column.id === "item_code" && value) {
            return `<a href="/app/item/${value}">${value}</a>`;
        }
        if (column.id === "reference_name" && data.reference_doctype) {
             return `<a href="/app/${data.reference_doctype.toLowerCase().replace(/ /g,'-')}/${value}">${value}</a>`;
        }
        return value;
    },
    "initial_depth": 1, // For tree view if using resources
    "onload": function(report) {
        // Custom rendering logic for calendar/timeline will go here
        // This report type might be better as a Page with a custom HTML field for FullCalendar
        // For a Script Report, we'd typically generate columns/data for a table.
        // To show a calendar, we'd need to inject HTML and JS.
        
        report.page.add_field({
            fieldname: 'calendar_view_html',
            fieldtype: 'HTML',
            label: 'Calendar View'
        });
        
        report.render_calendar = function(data) {
            if (!data) data = report.data; // Use report data if not passed
            var $calendar_area = $(report.page.fields_dict.calendar_view_html.wrapper).empty();
            $calendar_area.css({height: '600px', marginBottom: '20px'}); // Ensure calendar has height
            
            if (!data.length && !report.loading) {
                $calendar_area.html(`<p class="text-muted">${__("No data to display in calendar.")}</p>`);
                return;
            }

            // Ensure FullCalendar is loaded
            if (typeof FullCalendar === 'undefined') {
                $calendar_area.html(`<p class="text-danger">${__("FullCalendar library not loaded.")}</p>`);
                return;
            }
            
            let calendarEl = $calendar_area.get(0);

            let calendar = new FullCalendar.Calendar(calendarEl, {
                headerToolbar: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
                },
                initialDate: report.filters.from_date || frappe.datetime.now_date(),
                editable: false,
                eventLimit: true, // allow "more" link when too many events
                events: data.map(function(item) {
                    let title = item.item_code || 'Event';
                    if(item.serial_no) title += ` (${item.serial_no})`;
                    if(item.reference_name) title += ` - ${item.reference_name}`;
                    title += ` (${item.status || item.event_type})`;
                    
                    let color = '#3a87ad'; // Default
                    if(item.event_type === 'Rental Job') {
                        color = item.status === 'Completed' ? '#d3d3d3' : (item.status === 'Cancelled' ? '#f64c72' : '#28a745');
                    } else if (item.event_type === 'Maintenance Task') {
                        color = item.status === 'Completed' ? '#6c757d' : '#ffc107'; // Yellow for maintenance
                    }

                    return {
                        title: title,
                        start: item.start_date, 
                        end: frappe.datetime.add_days(item.end_date, 1), 
                        allDay: true, 
                        color: color,
                        url: item.reference_doctype && item.reference_name ? frappe.utils.get_form_link(item.reference_doctype, item.reference_name) : null
                    };
                }),
                eventDidMount: function(info) {
                    $(info.el).tooltip({ title: info.event.title });
                }
            });
            calendar.render();
            report.calendar_instance = calendar; // Store instance if needed
        };

        // Override the report render method to include calendar rendering
        let original_render = report.render;
        report.render = function(data) {
            original_render.call(report, data); 
            report.render_calendar(data); 
        };
        
        if(report.data && report.data.length > 0){
            report.render_calendar(report.data);
        } else {
            // Ensure calendar area is cleared if no data initially
             $(report.page.fields_dict.calendar_view_html.wrapper).empty().html(`<p class="text-muted">${__("Apply filters to load calendar data.")}</p>`);
        }
    }
};
