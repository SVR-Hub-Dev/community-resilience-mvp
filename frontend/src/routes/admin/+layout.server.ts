import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
	if (!locals.user) {
		throw redirect(302, '/auth/login?redirect=/admin');
	}

	if (locals.user.role !== 'admin') {
		throw redirect(302, '/?error=unauthorized');
	}

	return {
		// User is already passed from root layout
	};
};
