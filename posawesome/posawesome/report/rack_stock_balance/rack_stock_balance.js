// Copyright (c) 2026, Youssef Restom and contributors
// For license information, please see license.txt

frappe.query_reports["Rack Stock Balance"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_default("company")
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item Group"
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item",
			"get_query": function() {
				let item_group = frappe.query_report.get_filter_value("item_group");
				let filters = {
					"is_stock_item": 1
				};
				if (item_group) {
					filters["item_group"] = item_group;
				}
				return {
					filters: filters
				};
			}
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse",
			"get_query": function() {
				let company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						"company": company
					}
				};
			}
		},
		{
			"fieldname": "pos_profile",
			"label": __("POS Profile"),
			"fieldtype": "Link",
			"width": "80",
			"options": "POS Profile"
		},
		{
			"fieldname": "show_zero_values",
			"label": __("Show Zero Values"),
			"fieldtype": "Check",
			"default": 0
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "bal_qty") {
			if (data && data.bal_qty < 0) {
				value = "<span style='color:red'>" + value + "</span>";
			}
		}
		
		return value;
	},
	
	"onload": function(report) {
		report.page.add_inner_button(__("Stock Ledger"), function() {
			let filters = report.get_values();
			frappe.route_options = {
				"company": filters.company,
				"from_date": filters.from_date || frappe.datetime.add_months(frappe.datetime.get_today(), -1),
				"to_date": filters.to_date || frappe.datetime.get_today(),
				"item_code": filters.item_code || "",
				"warehouse": filters.warehouse || ""
			};
			frappe.set_route("query-report", "Stock Ledger");
		});
	}
};
