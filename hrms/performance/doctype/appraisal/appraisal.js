frappe.ui.form.on('Appraisal', {
    refresh: function(frm) {
        // Custom buttons
        if(frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Follow-up Appraisal'), function() {
                frappe.model.open_mapped_doc({
                    method: "hrms.performance.doctype.appraisal.appraisal.create_follow_up_appraisal",
                    frm: frm
                });
            }, __("Actions"));
        }
        
        if(!frm.doc.__islocal && frm.doc.status !== "Completed") {
            frm.add_custom_button(__('Calculate Score'), function() {
                frm.trigger("calculate_total_score");
            });
        }
        
        // Show previous appraisals in sidebar
        if(frm.doc.employee && !frm.doc.__islocal) {
            frappe.call({
                method: "hrms.performance.doctype.appraisal.appraisal.get_employee_previous_appraisals",
                args: {
                    employee: frm.doc.employee
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        let previous_appraisals = r.message
                            .filter(ap => ap.name !== frm.doc.name) // Filter out current appraisal
                            .slice(0, 5); // Limit to 5 most recent
                            
                        if (previous_appraisals.length > 0) {
                            frm.sidebar.add_user_action(__("Previous Appraisals")).addClass("btn-primary");
                            
                            previous_appraisals.forEach(function(appraisal) {
                                let label = `${frappe.datetime.str_to_user(appraisal.start_date)} to ${frappe.datetime.str_to_user(appraisal.end_date)} (${appraisal.score})`;
                                frm.sidebar.add_user_action(label, function() {
                                    frappe.set_route("Form", "Appraisal", appraisal.name);
                                });
                            });
                        }
                    }
                }
            });
        }
        
        // Set indicator colors
        if (frm.doc.status) {
            frm.set_indicator_formatter('status',
                function(doc) {
                    if (doc.status === 'Completed') return 'green';
                    if (doc.status === 'Cancelled') return 'red';
                    return 'orange';
                }
            );
        }
        
        // Show score visualization
        if(frm.doc.score) {
            // Create score visualization in the score_chart div
            $(frm.fields_dict.score_chart.wrapper).html("");
            
            let score_html = `
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar ${frm.doc.score >= 70 ? 'bg-success' : frm.doc.score >= 40 ? 'bg-warning' : 'bg-danger'}" 
                        role="progressbar" style="width: ${frm.doc.score}%;" 
                        aria-valuenow="${frm.doc.score}" aria-valuemin="0" aria-valuemax="100">
                        ${frm.doc.score}%
                    </div>
                </div>
                <div class="mt-2">
                    <span class="text-muted">Score Interpretation:</span>
                    <ul class="mt-1">
                        <li><span class="indicator green"></span> 70-100: Excellent Performance</li>
                        <li><span class="indicator orange"></span> 40-69: Meets Expectations</li>
                        <li><span class="indicator red"></span> 0-39: Needs Improvement</li>
                    </ul>
                </div>
            `;
            
            $(frm.fields_dict.score_chart.wrapper).html(score_html);
        }
    },
    
    onload: function(frm) {
        // Set filter for employee field
        frm.set_query("employee", function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
        
        // Set filter for appraisal template
        frm.set_query("appraisal_template", function() {
            return {
                filters: {
                    'enabled': 1
                }
            };
        });
        
        // Default values for new document
        if (frm.doc.__islocal) {
            frm.set_value("start_date", frappe.datetime.add_months(frappe.datetime.get_today(), -3));
            frm.set_value("end_date", frappe.datetime.get_today());
            
            // Set current user as employee if applicable
            if (frappe.session.user !== "Administrator") {
                frappe.db.get_value('Employee', {'user_id': frappe.session.user}, 'name', (r) => {
                    if (r && r.name) {
                        frm.set_value("employee", r.name);
                    }
                });
            }
        }
    },
    
    employee: function(frm) {
        if (frm.doc.employee) {
            // Get employee details
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Employee",
                    name: frm.doc.employee,
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value("employee_name", r.message.employee_name);
                        frm.set_value("department", r.message.department);
                        frm.set_value("designation", r.message.designation);
                    }
                }
            });
        }
    },
    
    appraisal_template: function(frm) {
        if (frm.doc.appraisal_template) {
            frm.call({
                method: "get_appraisal_template",
                doc: frm.doc,
                callback: function(r) {
                    frm.refresh_field("goals");
                }
            });
        }
    },
    
    calculate_total_score: function(frm) {
        let total_score = 0;
        let weighted_score = 0;
        let total_weights = 0;
        let goal_count = 0;
        
        // Calculate scores
        $.each(frm.doc.goals || [], function(i, goal) {
            if (goal.score) {
                total_score += flt(goal.score);
                goal_count++;
                
                if (goal.weight) {
                    weighted_score += flt(goal.score) * flt(goal.weight) / 100;
                    total_weights += flt(goal.weight);
                }
            }
        });
        
        // Set average and weighted scores
        if (goal_count) {
            frm.set_value("total_score", flt(total_score / goal_count, 2));
            frm.set_value("score", flt(weighted_score, 2));
            
            if (total_weights !== 100) {
                frappe.msgprint(__("Warning: Total weight for all goals should be 100%. Current total: {0}%", [total_weights]));
            }
        } else {
            frm.set_value("total_score", 0);
            frm.set_value("score", 0);
        }
    }
});

frappe.ui.form.on('Appraisal Goal', {
    score: function(frm, cdt, cdn) {
        frm.trigger("calculate_total_score");
    },
    
    weight: function(frm, cdt, cdn) {
        let total_weight = 0;
        
        // Calculate total weight
        $.each(frm.doc.goals || [], function(i, goal) {
            total_weight += flt(goal.weight);
        });
        
        if (total_weight > 100) {
            let row = locals[cdt][cdn];
            frappe.model.set_value(cdt, cdn, "weight", flt(row.weight) - (total_weight - 100));
            frappe.msgprint(__("Total weight cannot exceed 100%"));
        }
        
        frm.trigger("calculate_total_score");
    },
    
    goals_remove: function(frm) {
        frm.trigger("calculate_total_score");
    }
});
