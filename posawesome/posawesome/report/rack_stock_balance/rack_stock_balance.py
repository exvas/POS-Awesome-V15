# Copyright (c) 2026, Youssef Restom and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def execute(filters=None):
	if not filters:
		filters = {}
	
	validate_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("Please select a Company"))
	
	if not filters.get("from_date"):
		frappe.throw(_("From Date is required"))
	
	if not filters.get("to_date"):
		frappe.throw(_("To Date is required"))
	
	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
			frappe.throw(_("From Date cannot be greater than To Date"))


def get_columns():
	return [
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"width": 150
		},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 120
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 120
		},
		{
			"label": _("Rack ID"),
			"fieldname": "rack_id",
			"width": 100
		},
		{
			"label": _("POS Profile"),
			"fieldname": "pos_profile",
			"fieldtype": "Link",
			"options": "POS Profile",
			"width": 120
		},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90
		},
		{
			"label": _("Opening Qty"),
			"fieldname": "opening_qty",
			"fieldtype": "Float",
			"width": 100,
			"convertible": "qty"
		},
		{
			"label": _("Opening Value"),
			"fieldname": "opening_val",
			"fieldtype": "Currency",
			"width": 110,
			"options": "Company:company:default_currency"
		},
		{
			"label": _("In Qty"),
			"fieldname": "in_qty",
			"fieldtype": "Float",
			"width": 80,
			"convertible": "qty"
		},
		{
			"label": _("In Value"),
			"fieldname": "in_val",
			"fieldtype": "Currency",
			"width": 80,
			"options": "Company:company:default_currency"
		},
		{
			"label": _("Out Qty"),
			"fieldname": "out_qty",
			"fieldtype": "Float",
			"width": 80,
			"convertible": "qty"
		},
		{
			"label": _("Out Value"),
			"fieldname": "out_val",
			"fieldtype": "Currency",
			"width": 80,
			"options": "Company:company:default_currency"
		},
		{
			"label": _("Balance Qty"),
			"fieldname": "bal_qty",
			"fieldtype": "Float",
			"width": 100,
			"convertible": "qty"
		},
		{
			"label": _("Balance Value"),
			"fieldname": "bal_val",
			"fieldtype": "Currency",
			"width": 100,
			"options": "Company:company:default_currency"
		},
		{
			"label": _("Valuation Rate"),
			"fieldname": "val_rate",
			"fieldtype": "Currency",
			"width": 90,
			"convertible": "rate",
			"options": "Company:company:default_currency"
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 100
		}
	]


def get_data(filters):
	float_precision = cint(frappe.db.get_default("float_precision")) or 3
	
	# Get stock ledger entries
	sle = get_stock_ledger_entries(filters)
	
	# Get logical rack data
	rack_data = get_logical_rack_data(filters)
	
	# Get item details
	item_details = get_item_details(filters)
	
	# Process and combine data
	iwb_map = get_item_warehouse_map(sle, float_precision, filters)
	
	data = []
	for key in sorted(iwb_map):
		qty_dict = iwb_map[key]
		item_code, warehouse = key
		
		# Get rack information for this item/warehouse combination
		rack_info = rack_data.get((item_code, warehouse), {})
		item_info = item_details.get(item_code, {})
		
		if flt(qty_dict.bal_qty, float_precision) != 0 or filters.get("show_zero_values"):
			data.append({
				"item_code": item_code,
				"item_name": item_info.get("item_name", ""),
				"item_group": item_info.get("item_group", ""),
				"warehouse": warehouse,
				"rack_id": rack_info.get("rack_id", ""),
				"pos_profile": rack_info.get("pos_profile", ""),
				"stock_uom": item_info.get("stock_uom", ""),
				"opening_qty": flt(qty_dict.opening_qty, float_precision),
				"opening_val": flt(qty_dict.opening_val, float_precision),
				"in_qty": flt(qty_dict.in_qty, float_precision),
				"in_val": flt(qty_dict.in_val, float_precision),
				"out_qty": flt(qty_dict.out_qty, float_precision),
				"out_val": flt(qty_dict.out_val, float_precision),
				"bal_qty": flt(qty_dict.bal_qty, float_precision),
				"bal_val": flt(qty_dict.bal_val, float_precision),
				"val_rate": flt(qty_dict.bal_val / qty_dict.bal_qty, float_precision) if qty_dict.bal_qty else 0,
				"company": filters.get("company")
			})
	
	return data


def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	
	sle = frappe.db.sql("""
		SELECT
			item_code, warehouse, posting_date, posting_time,
			actual_qty, qty_after_transaction, stock_value_difference,
			stock_value, voucher_type, voucher_no, company
		FROM
			`tabStock Ledger Entry`
		WHERE
			docstatus < 2
			{conditions}
		ORDER BY
			item_code, warehouse, posting_date, posting_time, creation
	""".format(conditions=conditions), filters, as_dict=1)
	
	return sle


def get_logical_rack_data(filters):
	"""Get logical rack information for items"""
	conditions = ""
	if filters.get("item_code"):
		conditions += " AND item = %(item_code)s"
	if filters.get("pos_profile"):
		conditions += " AND pos_profile = %(pos_profile)s"
	
	racks = frappe.db.sql("""
		SELECT 
			item, rack_id, pos_profile, name
		FROM 
			`tabLogical Rack`
		WHERE 
			1=1
			{conditions}
	""".format(conditions=conditions), filters, as_dict=1)
	
	# Create a mapping of (item_code, warehouse) to rack info
	# Note: We need to join with warehouses from POS Profile
	rack_map = {}
	for rack in racks:
		if rack.pos_profile:
			# Get warehouses from POS Profile
			pos_warehouses = frappe.db.sql("""
				SELECT warehouse
				FROM `tabPOS Profile`
				WHERE name = %s
			""", rack.pos_profile, as_dict=1)
			
			for wh in pos_warehouses:
				if wh.warehouse:
					key = (rack.item, wh.warehouse)
					if key not in rack_map:
						rack_map[key] = {
							"rack_id": rack.rack_id,
							"pos_profile": rack.pos_profile
						}
	
	return rack_map


def get_item_details(filters):
	"""Get item details like name, group, UOM"""
	conditions = ""
	if filters.get("item_code"):
		conditions = " AND name = %(item_code)s"
	if filters.get("item_group"):
		conditions += " AND item_group = %(item_group)s"
	
	items = frappe.db.sql("""
		SELECT
			name, item_name, item_group, stock_uom
		FROM
			`tabItem`
		WHERE
			is_stock_item = 1
			{conditions}
	""".format(conditions=conditions), filters, as_dict=1)
	
	return {item.name: item for item in items}


def get_item_warehouse_map(sle, float_precision, filters):
	"""Process stock ledger entries to calculate opening, in, out, and balance quantities"""
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	
	for d in sle:
		key = (d.item_code, d.warehouse)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"opening_qty": 0.0,
				"opening_val": 0.0,
				"in_qty": 0.0,
				"in_val": 0.0,
				"out_qty": 0.0,
				"out_val": 0.0,
				"bal_qty": 0.0,
				"bal_val": 0.0
			})
		
		qty_dict = iwb_map[key]
		posting_date = getdate(d.posting_date)
		
		if posting_date < from_date:
			qty_dict.opening_qty += flt(d.actual_qty, float_precision)
			qty_dict.opening_val += flt(d.stock_value_difference, float_precision)
		elif posting_date >= from_date and posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty += flt(d.actual_qty, float_precision)
				qty_dict.in_val += flt(d.stock_value_difference, float_precision)
			else:
				qty_dict.out_qty += abs(flt(d.actual_qty, float_precision))
				qty_dict.out_val += abs(flt(d.stock_value_difference, float_precision))
		
		qty_dict.bal_qty = flt(qty_dict.opening_qty + qty_dict.in_qty - qty_dict.out_qty, float_precision)
		qty_dict.bal_val = flt(qty_dict.opening_val + qty_dict.in_val - qty_dict.out_val, float_precision)
	
	return iwb_map


def get_conditions(filters):
	conditions = ""
	
	if filters.get("company"):
		conditions += " AND company = %(company)s"
	
	# Don't filter by from_date here - we need all historical data to calculate opening balance
	# The date filtering is done in get_item_warehouse_map function
	
	if filters.get("to_date"):
		conditions += " AND posting_date <= %(to_date)s"
	else:
		frappe.throw(_("To Date is required"))
	
	if filters.get("item_code"):
		conditions += " AND item_code = %(item_code)s"
	
	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += """ AND warehouse in (SELECT name FROM `tabWarehouse`
				WHERE lft >= {0} AND rgt <= {1})""".format(
				warehouse_details.lft, warehouse_details.rgt
			)
	
	if filters.get("item_group"):
		conditions += " AND item_code in (SELECT name FROM `tabItem` WHERE item_group = %(item_group)s)"
	
	return conditions
