import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.user) {
		throw redirect(302, '/auth/login?redirect=/knowledge');
	}

	return {
		canEdit: locals.user.role === 'admin' || locals.user.role === 'editor'
	};
};
