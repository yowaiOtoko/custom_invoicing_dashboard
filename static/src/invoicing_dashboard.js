/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class InvoicingDashboard extends Component {
    static template = "custom_invoicing_dashboard.InvoicingDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.labels = {
            loading: _t("Loading…"),
            title: _t("Invoicing dashboard"),
            totalRevenue: _t("Total revenue"),
            unpaidInvoices: _t("Unpaid invoices"),
            draftQuotes: _t("Draft quotes"),
            addInvoice: _t("+ Invoice"),
            addQuote: _t("+ Quote"),
            recentInvoices: _t("Recent invoices"),
            recentQuotes: _t("Recent quotes"),
            colCustomer: _t("Customer"),
            colDate: _t("Date"),
            colTotal: _t("Total"),
            colStatus: _t("Status"),
            noInvoices: _t("No invoices yet."),
            noQuotes: _t("No quotes yet."),
        };
        this.state = useState({
            data: null,
            error: null,
        });
        onWillStart(async () => {
            try {
                this.state.data = await this.orm.call(
                    "custom_invoicing_dashboard.dashboard",
                    "get_dashboard_data",
                    []
                );
            } catch {
                this.state.error = _t("Could not load dashboard data.");
            }
        });
    }

    openInvoiceAction() {
        if (this.state.data?.invoice_action_id) {
            this.action.doAction(this.state.data.invoice_action_id);
        }
    }

    openQuoteAction() {
        if (this.state.data?.quote_action_id) {
            this.action.doAction(this.state.data.quote_action_id);
        }
    }
}

registry.category("actions").add("custom_invoicing_dashboard.invoicing", InvoicingDashboard);
