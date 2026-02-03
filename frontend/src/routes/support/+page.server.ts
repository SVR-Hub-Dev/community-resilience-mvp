import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { createApiClient } from '$lib/server/api';
import type { TicketListResponse, SupportTicket } from '$lib/types';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.user) {
		throw redirect(302, '/auth/login?redirect=/support');
	}

	const api = createApiClient(locals.user);

	try {
		const data = await api.get<TicketListResponse>('/support/tickets');
		return {
			tickets: data.tickets,
			total: data.total,
		};
	} catch (err) {
		console.error('Failed to load tickets:', err);
		return {
			tickets: [],
			total: 0,
			error: 'Failed to load tickets',
		};
	}
};

export const actions = {
	create: async ({ request, locals }) => {
		if (!locals.user) {
			throw redirect(302, '/auth/login');
		}

		const data = await request.formData();
		const subject = data.get('subject');
		const description = data.get('description');
		const priority = data.get('priority') || 'medium';

		// Validate
		if (!subject || typeof subject !== 'string' || subject.trim().length === 0) {
			return fail(400, { error: 'Subject is required' });
		}
		if (!description || typeof description !== 'string' || description.trim().length === 0) {
			return fail(400, { error: 'Description is required' });
		}

		const api = createApiClient(locals.user);

		try {
			const ticket = await api.post<SupportTicket>('/support/tickets', {
				subject: subject.trim(),
				description: description.trim(),
				priority,
			});

			// Redirect to the new ticket
			throw redirect(302, `/support/${ticket.id}`);
		} catch (err) {
			if (err instanceof Response || (err && typeof err === 'object' && 'status' in err && err.status === 302)) {
				throw err;
			}
			console.error('Failed to create ticket:', err);
			return fail(500, { error: 'Failed to create ticket' });
		}
	},
} satisfies Actions;
