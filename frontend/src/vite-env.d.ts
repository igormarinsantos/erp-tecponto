/// <reference types="vite/client" />

interface Window {
  tecpontoBoot?: {
		identity?: {
			company: string;
			address: string;
			cnpj: string;
			display_name: string;
			email: string;
			legal_name: string;
			logo_url: string;
			phone: string;
		};
    csrfToken?: string;
    site?: string;
  };
}
