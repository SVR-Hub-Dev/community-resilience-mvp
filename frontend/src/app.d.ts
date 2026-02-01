declare global {
	namespace App {
		interface Locals {
			user: {
				id: number;
				email: string;
				role: string;
			} | null;
		}
		// interface PageData {}
		// interface Platform {}
		// interface Error {}
	}
}

// TypeScript needs this to treat the file as a module
export {};
