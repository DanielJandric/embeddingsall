-- Schema updates for etats_locatifs normalisation

ALTER TABLE IF EXISTS public.etats_locatifs
    ADD COLUMN IF NOT EXISTS property_slug TEXT,
    ADD COLUMN IF NOT EXISTS property_name TEXT,
    ADD COLUMN IF NOT EXISTS property_commune TEXT,
    ADD COLUMN IF NOT EXISTS property_canton TEXT,
    ADD COLUMN IF NOT EXISTS property_postal_code TEXT,
    ADD COLUMN IF NOT EXISTS source_file TEXT,
    ADD COLUMN IF NOT EXISTS normalized_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS parsed_unit_count INT,
    ADD COLUMN IF NOT EXISTS parsed_surface_m2 NUMERIC,
    ADD COLUMN IF NOT EXISTS parsed_loyer_net_chf NUMERIC,
    ADD COLUMN IF NOT EXISTS parsed_loyer_brut_chf NUMERIC,
    ADD COLUMN IF NOT EXISTS tenants_sample TEXT[];

CREATE TABLE IF NOT EXISTS public.etats_locatifs_units (
    unit_id TEXT PRIMARY KEY,
    etat_id INT NOT NULL REFERENCES public.etats_locatifs(id) ON DELETE CASCADE,
    unit_index INT,
    reference TEXT,
    floor_label TEXT,
    usage_type TEXT,
    rooms NUMERIC,
    surface_m2 NUMERIC,
    tenant_name TEXT,
    tenant_first_name TEXT,
    tenant_last_name TEXT,
    tenant_company TEXT,
    tenant_is_company BOOLEAN,
    vacant BOOLEAN,
    status TEXT,
    lease_start DATE,
    lease_end DATE,
    loyer_net_chf NUMERIC,
    charges_chf NUMERIC,
    loyer_brut_chf NUMERIC,
    loyer_m2_chf NUMERIC,
    source_file TEXT,
    property_slug TEXT,
    raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_etats_locatifs_units_etat_id ON public.etats_locatifs_units(etat_id);
CREATE INDEX IF NOT EXISTS idx_etats_locatifs_units_property_slug ON public.etats_locatifs_units(property_slug);
CREATE INDEX IF NOT EXISTS idx_etats_locatifs_units_tenant ON public.etats_locatifs_units(tenant_name);


