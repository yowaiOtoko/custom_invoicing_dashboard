# AGENTS.md — custom_invoicing_dashboard

Facts for coding agents. Read once at the start of a session.
Never put passwords, API keys or tokens here: write the command that fetches them.

## What it is

Odoo addon (technical name `custom_invoicing_dashboard`) installed in every tenant: the
backend home dashboard (KPI cards, quick actions, recent invoices/quotes) and the
"Export comptable" page (FEC, Sage, CSV, XLSX, PDF ZIP). `post_init_hook` in `hooks.py`
makes the dashboard the home action for internal users.

## Layout

- `models/dashboard.py` (KPI data), `models/accounting_export.py` (exports), `models/res_users.py`
- `controllers/main.py` (download route)
- `static/src/invoicing_dashboard.{js,xml}`, `static/src/export_comptable.{js,xml}` (OWL, `web.assets_backend`)
- `views/*.xml` (actions, menus, company form), `i18n/`, `migrations/`, `tests/test_accounting_export.py`

## Branches and versions

- Only `main`. Manifest says `19.0.x`; the installer deploys the same `main.zip` to Odoo 18
  and 19 (dev single instance shows `18.0.x`). Keep code compatible with **both 18 and 19**.
- Bump `version` in `__manifest__.py` for any data/view change, or `-u` skips it.

## How code reaches Odoo (dev)

Not mounted. The installer downloads `main.zip` from GitHub into container
`erp-saas-installer-dev`: `/var/odoo/data/single/addons/18.0/custom_invoicing_dashboard`.

- After a push (the user decides when to push):
  `docker exec erp-saas-installer-dev /usr/local/bin/run-console.sh app:odoo:single-addons --update custom_invoicing_dashboard --db <db>`
- To test local, unpushed changes:
  ```
  docker cp . erp-saas-installer-dev:/var/odoo/data/single/addons/18.0/custom_invoicing_dashboard
  docker exec -u www-data erp-saas-installer-dev /usr/local/bin/python3.12 /var/www/odoo_single/odoo-bin \
    -c /var/odoo/config/odoo_single.conf -d odoo_sandbox1 -u custom_invoicing_dashboard --no-http --stop-after-init 2>&1 | tail -n 30
  ```
  JS/XML asset changes also need a browser hard reload (assets are bundled per DB).

## Tests

```
docker exec -u www-data erp-saas-installer-dev /usr/local/bin/python3.12 /var/www/odoo_single/odoo-bin \
  -c /var/odoo/config/odoo_single.conf -d odoo_sandbox1 -u custom_invoicing_dashboard \
  --test-enable --test-tags /custom_invoicing_dashboard --no-http --stop-after-init 2>&1 \
  | grep -E 'ERROR|FAIL|tests|Ran ' | tail -n 30
```

Copy the local files in first (see above), or the run tests the deployed version.
Syntax only: `python3 -m py_compile $(git diff --name-only -- '*.py') < /dev/null`.

## Runtime (local)

| What | Value |
|---|---|
| Odoo | http://127.0.0.1:8069, tenants `http://<tenant>.localhost:8069` |
| Tenant DBs | container `postgres`, DBs `odoo_*`; scratch tenant `odoo_sandbox1` |
| Odoo log | `docker exec erp-saas-installer-dev tail -n 60 /var/log/odoo/odoo_single.log` |

## Diagnostics

`scripts/dev/diag.sh`: deployed version per tenant DB, module errors in the Odoo log, Odoo health.

## Gotchas

- `xlsxwriter` is required for the XLSX export (standard Odoo dependency).
- Never run `app:purge-all` in the installer dev container (deletes `sandbox1`).
