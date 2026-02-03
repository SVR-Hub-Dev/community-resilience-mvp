import { redirect, error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { createApiClient } from '$lib/server/api';
import type { TicketListResponse } from '$lib/types';

export const load: PageServerLoad = async ({ locals, url }) => {
	if (!locals.user) {
		throw redirect(302, '/auth/login?redirect=/admin/support');
	}

	if (locals.user.role !== 'admin') {
		throw error(403, 'Admin access required');
	}

	const api = createApiClient(locals.user);

	// Get filter params
	const status = url.searchParams.get('status') || undefined;
	const priority = url.searchParams.get('priority') || undefined;

	try {
		const params = new URLSearchParams();
		if (status) params.set('status', status);
		if (priority) params.set('priority', priority);
		const query = params.toString();

		const data = await api.get<TicketListResponse>(
			`/admin/support/tickets${query ? `?${query}` : ''}`
		);

		return {
			tickets: data.tickets,
			total: data.total,
			filters: { status, priority },
		};
	} catch (err) {
		console.error('Failed to load tickets:', err);
		return {
			tickets: [],
			total: 0,
			filters: { status, priority },
			error: 'Failed to load tickets',
		};
	}
};
