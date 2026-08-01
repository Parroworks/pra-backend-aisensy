-- Clinic WhatsApp onboarding tables
CREATE TABLE IF NOT EXISTS public.clinic_whatsapp_accounts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    clinic_name TEXT NOT NULL,
    meta_business_portfolio_id TEXT NOT NULL,
    whatsapp_business_account_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.clinic_whatsapp_numbers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    whatsapp_account_id UUID NOT NULL REFERENCES public.clinic_whatsapp_accounts(id) ON DELETE CASCADE,
    phone_number_id TEXT NOT NULL UNIQUE,
    display_phone_number TEXT NOT NULL,
    quality_rating TEXT NULL,
    status TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
