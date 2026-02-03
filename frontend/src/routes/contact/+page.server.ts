import { fail } from '@sveltejs/kit';
import type { Actions } from './$types';
import { env } from '$env/dynamic/private';

const API_URL = env.API_URL || 'http://localhost:8000';

export const actions = {
	default: async ({ request }) => {
		const data = await request.formData();
		const name = data.get('name');
		const email = data.get('email');
		const subject = data.get('subject');
		const message = data.get('message');

		// Validate required fields
		if (!name || typeof name !== 'string' || name.trim().length === 0) {
			return fail(400, { error: 'Name is required', name: '', email, subject, message });
		}
		if (!email || typeof email !== 'string' || !email.includes('@')) {
			return fail(400, { error: 'Valid email is required', name, email: '', subject, message });
		}
		if (!subject || typeof subject !== 'string' || subject.trim().length === 0) {
			return fail(400, { error: 'Subject is required', name, email, subject: '', message });
		}
		if (!message || typeof message !== 'string' || message.trim().length === 0) {
			return fail(400, { error: 'Message is required', name, email, subject, message: '' });
		}

		try {
			const response = await fetch(`${API_URL}/contact`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					name: name.trim(),
					email: email.trim().toLowerCase(),
					subject: subject.trim(),
					message: message.trim(),
				}),
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				return fail(response.status, {
					error: errorData.detail || 'Failed to send message',
					name,
					email,
					subject,
					message,
				});
			}

			return { success: true };
		} catch (err) {
			console.error('Contact form submission error:', err);
			return fail(500, {
				error: 'Unable to send message. Please try again later.',
				name,
				email,
				subject,
				message,
			});
		}
	},
} satisfies Actions;
