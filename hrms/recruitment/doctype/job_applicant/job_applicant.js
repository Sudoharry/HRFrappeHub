frappe.ui.form.on('Job Applicant', {
    refresh: function(frm) {
        // Custom buttons
        if(frm.doc.status === "Accepted") {
            frm.add_custom_button(__('Create Employee'), function() {
                frappe.model.open_mapped_doc({
                    method: "hrms.recruitment.doctype.job_applicant.job_applicant.create_employee_from_applicant",
                    frm: frm
                });
            }, __("Actions"));
        }
        
        if(frm.doc.status !== "Rejected" && !frm.doc.__islocal) {
            frm.add_custom_button(__('Schedule Interview'), function() {
                frappe.model.open_mapped_doc({
                    method: "hrms.recruitment.doctype.job_applicant.job_applicant.schedule_interview",
                    frm: frm
                });
            }, __("Actions"));
        }
        
        if(!frm.doc.__islocal) {
            // Add communication buttons
            frm.add_custom_button(__('Send Email'), function() {
                if(frm.doc.email) {
                    new frappe.views.CommunicationComposer({
                        doc: frm.doc,
                        frm: frm,
                        subject: __('Application for {0}', [frm.doc.job_title]),
                        recipients: frm.doc.email,
                        attach_document_print: true,
                    });
                } else {
                    frappe.msgprint(__("Email ID not found. Please enter email before sending."));
                }
            }, __("Communication"));
        }
        
        // Set indicator colors
        if (frm.doc.status) {
            frm.set_indicator_formatter('status',
                function(doc) {
                    let indicator = 'blue';
                    if (doc.status === 'Accepted') {
                        indicator = 'green';
                    } else if (doc.status === 'Rejected') {
                        indicator = 'red';
                    } else if (doc.status === 'Hold') {
                        indicator = 'orange';
                    } else if (doc.status === 'Replied') {
                        indicator = 'cyan';
                    }
                    return indicator;
                }
            );
        }
        
        // Show resume in sidebar
        if(frm.doc.resume_attachment) {
            frm.sidebar.add_user_action(__("View Resume"), function() {
                window.open(
                    frappe.model.get_attached_file_url(frm.doc.resume_attachment),
                    '_blank'
                );
            });
        }
        
        // Show application history
        if(!frm.doc.__islocal) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Communication",
                    filters: {
                        reference_doctype: "Job Applicant",
                        reference_name: frm.doc.name
                    },
                    fields: ["subject", "communication_date", "communication_medium", "content"],
                    order_by: "communication_date desc"
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        var html = "<div class='timeline'>";
                        r.message.forEach(function(comm) {
                            html += "<div class='timeline-item'>";
                            html += "<div class='timeline-dot'></div>";
                            html += "<div class='timeline-content'>";
                            html += "<div class='timeline-title'>" + comm.subject + "</div>";
                            html += "<div class='timeline-date'>" + frappe.datetime.prettyDate(comm.communication_date) + "</div>";
                            html += "<div class='timeline-text'>" + comm.content + "</div>";
                            html += "</div></div>";
                        });
                        html += "</div>";
                        
                        // Add the timeline to a custom section
                        $(frm.fields_dict.communication_history.wrapper).html(html);
                    } else {
                        $(frm.fields_dict.communication_history.wrapper).html("<p>No communication history</p>");
                    }
                }
            });
        }
    },
    
    onload: function(frm) {
        // Set filter for job_title field to only show Open jobs
        frm.set_query("job_title", function() {
            return {
                filters: {
                    "status": "Open"
                }
            };
        });
        
        // Default values for new document
        if (frm.doc.__islocal) {
            frm.set_value("status", "Open");
            
            // Pre-fill job title if provided in route options
            if (frappe.route_options && frappe.route_options.job_title) {
                frm.set_value("job_title", frappe.route_options.job_title);
            }
        }
    },
    
    job_title: function(frm) {
        if (frm.doc.job_title) {
            // Get job opening details
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Job Opening",
                    name: frm.doc.job_title,
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("designation", r.message.designation);
                        frm.set_value("department", r.message.department);
                        frm.set_value("company", r.message.company);
                    }
                }
            });
        }
    },
    
    applicant_name: function(frm) {
        // Auto-suggest an email based on name if not provided
        if (frm.doc.applicant_name && !frm.doc.email) {
            // This would be just a basic example - normally you wouldn't auto-generate emails
            // Just leaving as placeholder since it's a good usability practice to show the field
        }
    },
    
    email: function(frm) {
        // Simple email validation
        if (frm.doc.email) {
            var valid_email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(frm.doc.email);
            if (!valid_email) {
                frappe.msgprint(__("Please enter a valid email address"));
            }
        }
    },
    
    phone: function(frm) {
        // Simple phone validation
        if (frm.doc.phone) {
            var valid_phone = /^\d+$/.test(frm.doc.phone);
            if (!valid_phone) {
                frappe.msgprint(__("Phone number should contain only digits"));
            }
        }
    },
    
    status: function(frm) {
        // If status is changed to Replied, promt for the response
        if (frm.doc.status === "Replied" && frm.doc.__unsaved) {
            var d = new frappe.ui.Dialog({
                title: __('Response Details'),
                fields: [
                    {
                        label: __('Response Date'),
                        fieldname: 'response_date',
                        fieldtype: 'Date',
                        default: frappe.datetime.get_today()
                    },
                    {
                        label: __('Medium'),
                        fieldname: 'response_medium',
                        fieldtype: 'Select',
                        options: 'Email\nPhone\nIn Person\nOther'
                    },
                    {
                        label: __('Response Details'),
                        fieldname: 'response_details',
                        fieldtype: 'Small Text'
                    }
                ],
                primary_action_label: __('Save'),
                primary_action: function() {
                    var values = d.get_values();
                    // Save as a communication
                    frappe.call({
                        method: "frappe.client.insert",
                        args: {
                            doc: {
                                doctype: "Communication",
                                reference_doctype: "Job Applicant",
                                reference_name: frm.doc.name,
                                subject: __("Response to Applicant"),
                                communication_date: values.response_date,
                                communication_medium: values.response_medium,
                                content: values.response_details,
                                sent_or_received: "Sent"
                            }
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                            }
                        }
                    });
                    d.hide();
                }
            });
            d.show();
        }
    }
});
