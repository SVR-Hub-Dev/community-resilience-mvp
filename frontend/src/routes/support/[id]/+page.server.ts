import { fail, redirect, error } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { createApiClient, ApiError } from '$lib/server/api';
import type { TicketDetail, TicketResponse } from '$lib/types';

export const load: PageServerLoad = async ({ locals, params }) => {
	if (!locals.user) {
		throw redirect(302, '/auth/login?redirect=/support/' + params.id);
	}

	const api = createApiClient(locals.user);
	const ticketId = parseInt(params.id, 10);

	if (isNaN(ticketId)) {
		throw error(400, 'Invalid ticket ID');
	}

	try {
		const ticket = await api.get<TicketDetail>(`/support/tickets/${ticketId}`);
		return { ticket };
	} catch (err) {
		if (err instanceof ApiError) {
			if (err.status === 404) {
				throw error(404, 'Ticket not found');
			}
			if (err.status === 403) {
				throw error(403, 'Access denied');
			}
		}
		console.error('Failed to load ticket:', err);
		throw error(500, 'Failed to load ticket');
	}
};

export const actions = {
	respond: async ({ request, locals, params }) => {
		if (!locals.user) {
			throw redirect(302, '/auth/login');
		}

		const data = await request.formData();
		const message = data.get('message');
		const ticketId = parseInt(params.id, 10);

		if (!message || typeof message !== 'string' || message.trim().length === 0) {
			return fail(400, { error: 'Message is required' });
		}

		const api = createApiClient(locals.user);

		try {
			await api.post<TicketResponse>(`/support/tickets/${ticketId}/responses`, {
				message: message.trim(),
			});

			return { success: true };
		} catch (err) {
			console.error('Failed to add response:', err);
			return fail(500, { error: 'Failed to add response' });
		}
	},
} satisfies Actions;
