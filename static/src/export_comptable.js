/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class ExportComptable extends Component {
    static template = "custom_invoicing_dashboard.ExportComptable";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.labels = {
            loading: _t("Loading…"),
            title: _t("Export comptable"),
            back: _t("Back to dashboard"),
            period: _t("Period"),
            format: _t("Format"),
            export: _t("Export"),
            year: _t("Year"),
            from: _t("From"),
            to: _t("To"),
            invoiceCount: _t("invoices"),
            noInvoices: _t("No posted customer invoice in this period."),
            invalidRange: _t("Please select a valid date range."),
            exportFailed: _t("Export failed."),
        };
        this.formats = [
            { value: "fec", label: _t("FEC") },
            { value: "sage", label: _t("Sage") },
            { value: "csv", label: _t("CSV") },
            { value: "xlsx", label: _t("XLSX") },
            { value: "pdf", label: _t("PDF (invoices)") },
            { value: "fecpdf", label: _t("FEC + PDFs (zip)") },
            { value: "pennylane", label: _t("Pennylane") },
        ];
        this.presets = [
            { value: "current_year", label: _t("Current year") },
            { value: "previous_year", label: _t("Previous year") },
            { value: "ytd", label: _t("Year to date") },
            { value: "last_6_months", label: _t("Last 6 months") },
            { value: "specific_year", label: _t("Specific year") },
            { value: "custom", label: _t("Custom range") },
        ];
        this.state = useState({
            data: null,
            error: null,
            preset: "current_year",
            year: new Date().getFullYear(),
            date_from: "",
            date_to: "",
            format: "fec",
            exporting: false,
            invoice_count: null,
        });
        onWillStart(async () => {
            try {
                this.state.data = await this.orm.call(
                    "custom_invoicing_dashboard.accounting_export",
                    "get_page_data",
                    []
                );
            } catch {
                this.state.error = _t("Could not load export page.");
            }
        });
    }

    get years() {
        const years = [...(this.state.data?.years || [])];
        const current = new Date().getFullYear();
        if (!years.includes(current)) {
            years.push(current);
        }
        return years.sort((a, b) => b - a);
    }

    get rangeLabel() {
        const { from, to } = this.computeRange();
        if (!from || !to) {
            return "";
        }
        return `${this.formatDate(from)} → ${this.formatDate(to)}`;
    }

    get countLabel() {
        return this.state.invoice_count === null
            ? ""
            : `${this.state.invoice_count} ${this.labels.invoiceCount}`;
    }

    formatDate(d) {
        if (!d) {
            return "";
        }
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${day}`;
    }

    computeRange() {
        const now = new Date();
        const startYear = (y) => new Date(y, 0, 1);
        const endYear = (y) => new Date(y, 11, 31, 23, 59, 59);
        let from = null;
        let to = null;
        switch (this.state.preset) {
            case "current_year":
                from = startYear(now.getFullYear());
                to = endYear(now.getFullYear());
                break;
            case "previous_year":
                from = startYear(now.getFullYear() - 1);
                to = endYear(now.getFullYear() - 1);
                break;
            case "ytd":
                from = startYear(now.getFullYear());
                to = now;
                break;
            case "last_6_months":
                from = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
                to = now;
                break;
            case "specific_year":
                from = startYear(this.state.year);
                to = endYear(this.state.year);
                break;
            case "custom":
                from = this.state.date_from ? new Date(this.state.date_from) : null;
                to = this.state.date_to ? new Date(this.state.date_to) : null;
                break;
        }
        return { from, to };
    }

    setPreset(ev) {
        this.state.preset = ev.currentTarget.dataset.preset;
        this.refreshCount();
    }

    setFormat(ev) {
        this.state.format = ev.currentTarget.dataset.format;
    }

    onYearChange(ev) {
        this.state.year = parseInt(ev.target.value, 10);
        this.refreshCount();
    }

    onDateChange() {
        this.refreshCount();
    }

    async refreshCount() {
        const { from, to } = this.computeRange();
        if (!from || !to) {
            this.state.invoice_count = null;
            return;
        }
        try {
            this.state.invoice_count = await this.orm.call(
                "custom_invoicing_dashboard.accounting_export",
                "count_moves",
                [this.formatDate(from), this.formatDate(to)]
            );
        } catch {
            this.state.invoice_count = null;
        }
    }

    async exportFile() {
        const { from, to } = this.computeRange();
        if (!from || !to) {
            this.notification.add(this.labels.invalidRange, { type: "warning" });
            return;
        }
        this.state.exporting = true;
        try {
            const count = await this.orm.call(
                "custom_invoicing_dashboard.accounting_export",
                "count_moves",
                [this.formatDate(from), this.formatDate(to)]
            );
            if (!count) {
                this.notification.add(this.labels.noInvoices, { type: "warning" });
                return;
            }
            const url =
                `/custom/export/comptable/${encodeURIComponent(this.state.format)}` +
                `?date_from=${this.formatDate(from)}&date_to=${this.formatDate(to)}`;
            const a = document.createElement("a");
            a.href = url;
            a.download = "";
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch {
            this.notification.add(this.labels.exportFailed, { type: "danger" });
        } finally {
            this.state.exporting = false;
        }
    }

    goBack() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "custom_invoicing_dashboard.invoicing",
        });
    }
}

registry.category("actions").add("custom_invoicing_dashboard.export_comptable", ExportComptable);
