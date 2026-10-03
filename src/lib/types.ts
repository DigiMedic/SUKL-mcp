export interface MedicineBasic {
  sukl_code: string;
  name: string;
  strength: string | null;
  form: string | null;
  package: string | null;
  atc_code: string | null;
  substance: string | null;
  holder: string | null;
  registration_status: string | null;
}

export interface MedicineDetail extends MedicineBasic {
  registration_number: string | null;
  registration_valid_until: string | null;
  dispensing: string | null;
  legal_status: string | null;
  route_of_administration: string | null;
  indication_group: string | null;
  mrp_number: string | null;
  parallel_import: boolean | null;
}

export interface ReimbursementInfo {
  sukl_code: string;
  reimbursement_group: string | null;
  max_price: number | null;
  reimbursement_amount: number | null;
  patient_surcharge: number | null;
  reimbursement_conditions: string | null;
  valid_from: string | null;
  valid_until: string | null;
}

export interface AvailabilityInfo {
  sukl_code: string;
  name: string;
  status: "available" | "limited" | "unavailable" | "unknown";
  last_checked: string | null;
  distribution_status: string | null;
  expected_availability: string | null;
  notes: string | null;
}

export interface Pharmacy {
  id: string;
  name: string;
  address: string;
  city: string;
  postal_code: string;
  phone: string | null;
  email: string | null;
  opening_hours: string | null;
  latitude: number | null;
  longitude: number | null;
  distance_km: number | null;
  is_24h: boolean | null;
  has_emergency_service?: boolean;
  has_erecept: boolean;
}

export interface ATCInfo {
  code: string;
  name_cs: string;
  name_en: string | null;
  level: number;
  parent_code: string | null;
  description: string | null;
}

export interface DocumentContent {
  sukl_code: string;
  document_type: "PIL" | "SPC";
  title: string;
  content: string;
  sections: { heading: string; content: string }[];
  last_updated: string | null;
  language: string;
  document_url: string | null;
}
