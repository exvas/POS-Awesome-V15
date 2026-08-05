# -*- coding: utf-8 -*-
# Copyright (c) 2021, Youssef Restom and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, add_days
from posawesome.posawesome.doctype.pos_coupon.pos_coupon import update_coupon_code_count
from posawesome.posawesome.api.posapp import get_company_domain
from posawesome.posawesome.doctype.delivery_charges.delivery_charges import (
    get_applicable_delivery_charges,
)

 
def after_insert(doc, method):
    disable_rounded_total(doc)
def validate(doc, method):
    validate_shift(doc)
    set_patient(doc)
    auto_set_delivery_charges(doc)
    calc_delivery_charges(doc)
    


def before_submit(doc, method):
    add_loyalty_point(doc)
    create_sales_order(doc)
    create_quotation(doc)
    update_coupon(doc, "used")


def before_cancel(doc, method):
    update_coupon(doc, "cancelled")


def add_loyalty_point(invoice_doc):
    for offer in invoice_doc.posa_offers:
        if offer.offer == "Loyalty Point":
            original_offer = frappe.get_doc("POS Offer", offer.offer_name)
            if original_offer.loyalty_points > 0:
                loyalty_program = frappe.get_value(
                    "Customer", invoice_doc.customer, "loyalty_program"
                )
                if not loyalty_program:
                    loyalty_program = original_offer.loyalty_program
                doc = frappe.get_doc(
                    {
                        "doctype": "Loyalty Point Entry",
                        "loyalty_program": loyalty_program,
                        "loyalty_program_tier": original_offer.name,
                        "customer": invoice_doc.customer,
                        "invoice_type": "Sales Invoice",
                        "invoice": invoice_doc.name,
                        "loyalty_points": original_offer.loyalty_points,
                        "expiry_date": add_days(invoice_doc.posting_date, 10000),
                        "posting_date": invoice_doc.posting_date,
                        "company": invoice_doc.company,
                    }
                )
                doc.insert(ignore_permissions=True)


def create_sales_order(doc):
    if (
        doc.posa_pos_opening_shift
        and doc.pos_profile
        and doc.is_pos
        and doc.posa_delivery_date
        and not doc.update_stock
        and frappe.get_value("POS Profile", doc.pos_profile, "posa_allow_sales_order")
    ):
        sales_order_doc = make_sales_order(doc.name)
        if sales_order_doc:
            sales_order_doc.posa_notes = doc.posa_notes
            sales_order_doc.flags.ignore_permissions = True
            sales_order_doc.flags.ignore_account_permission = True
            sales_order_doc.save()
            sales_order_doc.submit()
            url = frappe.utils.get_url_to_form(
                sales_order_doc.doctype, sales_order_doc.name
            )
            msgprint = "Sales Order Created at <a href='{0}'>{1}</a>".format(
                url, sales_order_doc.name
            )
            frappe.msgprint(
                _(msgprint), title="Sales Order Created", indicator="green", alert=True
            )
            i = 0
            for item in sales_order_doc.items:
                doc.items[i].sales_order = sales_order_doc.name
                doc.items[i].so_detail = item.name
                i += 1


def make_sales_order(source_name, target_doc=None, ignore_permissions=True):
    def set_missing_values(source, target):
        target.ignore_pricing_rule = 1
        target.flags.ignore_permissions = ignore_permissions
        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(obj, target, source_parent):
        target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)
        target.delivery_date = (
            obj.posa_delivery_date or source_parent.posa_delivery_date
        )

    doclist = get_mapped_doc(
        "Sales Invoice",
        source_name,
        {
            "Sales Invoice": {
                "doctype": "Sales Order",
            },
            "Sales Invoice Item": {
                "doctype": "Sales Order Item",
                "field_map": {
                    "cost_center": "cost_center",
                    "Warehouse": "warehouse",
                    "delivery_date": "posa_delivery_date",
                    "posa_notes": "posa_notes",
                },
                "postprocess": update_item,
            },
            "Sales Taxes and Charges": {
                "doctype": "Sales Taxes and Charges",
                "add_if_empty": True,
            },
            "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
            "Payment Schedule": {"doctype": "Payment Schedule", "add_if_empty": True},
        },
        target_doc,
        set_missing_values,
        ignore_permissions=ignore_permissions,
    )

    return doclist


def update_coupon(doc, transaction_type):
    for coupon in doc.posa_coupons:
        if not coupon.applied:
            continue
        update_coupon_code_count(coupon.coupon, transaction_type)


def set_patient(doc):
    domain = get_company_domain(doc.company)
    if domain != "Healthcare":
        return
    patient_list = frappe.get_all(
        "Patient", filters={"customer": doc.customer}, page_length=1
    )
    if len(patient_list) > 0:
        doc.patient = patient_list[0].name


def auto_set_delivery_charges(doc):
    if not doc.pos_profile:
        return
    if not frappe.get_cached_value(
        "POS Profile", doc.pos_profile, "posa_auto_set_delivery_charges"
    ):
        return

    delivery_charges = get_applicable_delivery_charges(
        doc.company,
        doc.pos_profile,
        doc.customer,
        doc.shipping_address_name,
        doc.posa_delivery_charges,
        restrict=True,
    )

    if doc.posa_delivery_charges:
        if doc.posa_delivery_charges_rate:
            return
        else:
            if len(delivery_charges) > 0:
                doc.posa_delivery_charges_rate = delivery_charges[0].rate
    else:
        if len(delivery_charges) > 0:
            doc.posa_delivery_charges = delivery_charges[0].name
            doc.posa_delivery_charges_rate = delivery_charges[0].rate
        else:
            doc.posa_delivery_charges = None
            doc.posa_delivery_charges_rate = None


def calc_delivery_charges(doc):
    if not doc.pos_profile:
        return

    old_doc = None
    calculate_taxes_and_totals = False
    if not doc.is_new():
        old_doc = doc.get_doc_before_save()
        if not doc.posa_delivery_charges and not old_doc.posa_delivery_charges:
            return
    else:
        if not doc.posa_delivery_charges:
            return
    if not doc.posa_delivery_charges:
        doc.posa_delivery_charges_rate = 0

    charges_doc = None
    if doc.posa_delivery_charges:
        charges_doc = frappe.get_cached_doc(
            "Delivery Charges", doc.posa_delivery_charges
        )
        doc.posa_delivery_charges_rate = charges_doc.default_rate
        charges_profile = next(
            (i for i in charges_doc.profiles if i.pos_profile == doc.pos_profile), None
        )
        if charges_profile:
            doc.posa_delivery_charges_rate = charges_profile.rate

    if old_doc and old_doc.posa_delivery_charges:
        old_charges = next(
            (
                i
                for i in doc.taxes
                if i.charge_type == "Actual"
                and i.description == old_doc.posa_delivery_charges
            ),
            None,
        )
        if old_charges:
            doc.taxes.remove(old_charges)
            calculate_taxes_and_totals = True

    if doc.posa_delivery_charges:
        doc.append(
            "taxes",
            {
                "charge_type": "Actual",
                "description": doc.posa_delivery_charges,
                "tax_amount": doc.posa_delivery_charges_rate,
                "cost_center": charges_doc.cost_center,
                "account_head": charges_doc.shipping_account,
            },
        )
        calculate_taxes_and_totals = True

    if calculate_taxes_and_totals:
        doc.calculate_taxes_and_totals()


def validate_shift(doc):
    if doc.posa_pos_opening_shift and doc.pos_profile and doc.is_pos:
        # check if shift is open
        shift = frappe.get_cached_doc("POS Opening Shift", doc.posa_pos_opening_shift)
        if shift.status != "Open":
            frappe.throw(_("POS Shift {0} is not open").format(shift.name))
        # check if shift is for the same profile
        if shift.pos_profile != doc.pos_profile:
            frappe.throw(
                _("POS Opening Shift {0} is not for the same POS Profile").format(
                    shift.name
                )
            )
        # check if shift is for the same company
        if shift.company != doc.company:
            frappe.throw(
                _("POS Opening Shift {0} is not for the same company").format(
                    shift.name
                )
            )

@frappe.whitelist()
def get_item_price_for_uom(item_code, price_list, uom, customer=None, company=None, currency=None, conversion_factor=1):

    from erpnext.stock.get_item_details import get_item_price
    
    item_price_args = {
        "item_code": item_code,
        "price_list": price_list,
        "uom": uom,
        "customer": customer,
        "company": company,
        "currency": currency
    }
    
    # Get item price for specific UOM
    price_list_rate = get_item_price(item_price_args, item_code, ignore_party=True)
    
    if price_list_rate:
        return {
            "price_list_rate": price_list_rate[0][1],  # price_list_rate from the tuple
            "uom": uom,
            "found_specific_uom": True
        }
    
    item_doc = frappe.get_doc("Item", item_code)
    stock_uom = item_doc.stock_uom
    
    if stock_uom != uom:
        item_price_args["uom"] = stock_uom
        base_price = get_item_price(item_price_args, item_code, ignore_party=True)
        
        if base_price:
            uom_conversion = frappe.db.get_value(
                "UOM Conversion Detail",
                {"parent": item_code, "uom": uom},
                "conversion_factor"
            )
            
            if uom_conversion:
                converted_price = base_price[0][1] * float(uom_conversion)
                return {
                    "price_list_rate": converted_price,
                    "uom": uom,
                    "found_specific_uom": False,
                    "converted_from_stock_uom": True,
                    "stock_uom_price": base_price[0][1],
                    "conversion_factor": uom_conversion
                }
    
    return None


def make_quotation(source_name, target_doc=None, ignore_permissions=True):
    """Create Quotation from Sales Invoice"""
    def set_missing_values(source, target):
        target.ignore_pricing_rule = 1
        target.flags.ignore_permissions = ignore_permissions
        # Set quotation specific fields
        target.quotation_to = "Customer"
        target.order_type = "Sales"
        # Set valid till date to 30 days from today
        target.valid_till = add_days(frappe.utils.nowdate(), 30)
        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(obj, target, source_parent):
        target.qty = flt(obj.qty)
        if hasattr(obj, 'posa_delivery_date') and obj.posa_delivery_date:
            target.delivery_date = obj.posa_delivery_date
        elif hasattr(source_parent, 'posa_delivery_date') and source_parent.posa_delivery_date:
            target.delivery_date = source_parent.posa_delivery_date

    doclist = get_mapped_doc(
        "Sales Invoice",
        source_name,
        {
            "Sales Invoice": {
                "doctype": "Quotation",
                "field_map": {
                    "customer": "party_name",
                    "customer_name": "customer_name",
                },
            },
            "Sales Invoice Item": {
                "doctype": "Quotation Item",
                "field_map": {
                    "cost_center": "cost_center",
                    "warehouse": "warehouse",
                    "posa_notes": "posa_notes",
                },
                "postprocess": update_item,
            },
            "Sales Taxes and Charges": {
                "doctype": "Sales Taxes and Charges",
                "add_if_empty": True,
            },
            "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
        },
        target_doc,
        set_missing_values,
        ignore_permissions=ignore_permissions,
    )

    return doclist


def create_quotation(doc):
    """Create quotation from POS invoice when quotation type is selected"""
    if (
        doc.posa_pos_opening_shift
        and doc.pos_profile
        and doc.is_pos
        and frappe.get_value("POS Profile", doc.pos_profile, "posa_allow_create_quotation")
        and getattr(doc, 'posa_invoice_type', None) == 'Quotation'
    ):
        quotation_doc = make_quotation(doc.name)
        if quotation_doc:
            quotation_doc.posa_notes = getattr(doc, 'posa_notes', '')
            quotation_doc.flags.ignore_permissions = True
            quotation_doc.flags.ignore_account_permission = True
            quotation_doc.save()
            
            # Submit the quotation
            quotation_doc.submit()
            
            # Mark as printed for POS workflow
            quotation_doc.posa_is_printed = 1
            quotation_doc.save()
            
            url = frappe.utils.get_url_to_form(
                quotation_doc.doctype, quotation_doc.name
            )
            msgprint = "Quotation Created and Submitted at <a href='{0}'>{1}</a>".format(
                url, quotation_doc.name
            )
            frappe.msgprint(
                _(msgprint), title="Quotation Created", indicator="blue", alert=True
            )
            
            # Store quotation reference for printing
            doc.posa_quotation_ref = quotation_doc.name


@frappe.whitelist()
def create_quotation_from_invoice(sales_invoice):
    """Create quotation from sales invoice and submit it"""
    quotation = make_quotation(sales_invoice, ignore_permissions=True)
    quotation.flags.ignore_permissions = True
    quotation.flags.ignore_account_permission = True
    
    # Set valid till date to 30 days from today
    quotation.valid_till = add_days(frappe.utils.nowdate(), 30)
    
    # Save first
    quotation.save()
    
    # Then submit
    quotation.submit()
    
    return quotation.as_dict()


def load_quotation_print_page(quotation_name, pos_profile):
    """Load print page for quotation"""
    from urllib.parse import quote

    from frappe.utils import get_url

    print_format = frappe.get_cached_value(
        "POS Profile", pos_profile, "posa_quotation_print_format"
    )

    if not print_format or not frappe.db.exists("Print Format", print_format):
        # Fall back to any enabled Quotation format, then to the generic one
        fallback = frappe.get_all(
            "Print Format",
            filters={"doc_type": "Quotation", "disabled": 0},
            pluck="name",
            order_by="name",
            limit=1,
        )
        print_format = fallback[0] if fallback else "Standard"

    url = (
        get_url() +
        "/printview?doctype=Quotation&name=" +
        quote(quotation_name) +
        "&trigger_print=1" +
        "&format=" +
        quote(print_format) +
        "&no_letterhead=0"
    )

    return url


@frappe.whitelist()
def print_quotation(quotation_name, pos_profile):
    """Print quotation document"""
    try:
        print_url = load_quotation_print_page(quotation_name, pos_profile)
        return {
            "success": True,
            "print_url": print_url,
            "message": f"Quotation {quotation_name} ready for printing"
        }
    except Exception as e:
        frappe.log_error(f"Error printing quotation {quotation_name}: {str(e)}")
        return {
            "success": False,
            "message": f"Error printing quotation: {str(e)}"
        }