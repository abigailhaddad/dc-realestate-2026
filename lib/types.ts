export type MonthlyRow = {
  month: string;
  residential_count: number;
  residential_median: number | null;
  commercial_count: number;
  commercial_median: number | null;
  residential_count_avg12: number | null;
  commercial_count_avg12: number | null;
  residential_median_avg12: number | null;
  commercial_median_avg12: number | null;
  single_family_count: number;
  single_family_median: number | null;
  condo_count: number;
  condo_median: number | null;
  multifamily_count: number;
  multifamily_median: number | null;
  office_count: number;
  office_median: number | null;
  retail_count: number;
  retail_median: number | null;
  hotel_lodging_count: number;
  hotel_lodging_median: number | null;
  industrial_count: number;
  industrial_median: number | null;
  commercial_other_count: number;
  commercial_other_median: number | null;
  institutional_count: number;
  institutional_median: number | null;
  vacant_count: number;
  vacant_median: number | null;
  other_count: number;
  other_median: number | null;
};

export type ByUseRow = {
  category: string;
  label: string;
  total_count: number;
  median_price: number;
  counts_by_year: Record<string, number>;
  medians_by_year: Record<string, number>;
  count_2026_annualized: number;
  median_2024: number;
  median_2025: number;
  median_2026_ytd: number;
  count_2024: number;
  count_2025: number;
  count_2026_ytd: number;
};

export type ClusterGeo = {
  cluster_num: number;
  cluster_name: string;
  rings: number[][][];
  count_recent: number;
  count_recent_residential: number;
  count_recent_commercial: number;
  median_recent: number;
  counts_by_year: Record<string, { all: number; residential: number; commercial: number }>;
};

export type ByClusterRow = {
  cluster_num: number;
  cluster_name: string;
  total_count: number;
  median_price: number;
  count_2024: number;
  count_2025: number;
  count_2026_ytd: number;
};

export type TopSale = {
  sale_date: string;
  sale_price: number;
  address: string;
  use_category: string;
  use_description: string;
  cluster_name: string;
  buyer: string;
  building_sqft: number | null;
  lat: number | null;
  lon: number | null;
};

export type Summary = {
  generated_at: string;
  first_sale: string;
  last_sale: string;
  total_sales: number;
  count_2020: number;
  count_2021: number;
  count_2022: number;
  count_2023: number;
  count_2024: number;
  count_2025: number;
  count_2026_ytd: number;
};
