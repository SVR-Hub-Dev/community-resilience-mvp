/**
 * Authentication utilities for Svelte 5.
 *
 * This module provides helper functions for checking user roles and permissions.
 * User data is sourced from the server via event.locals.user, passed through
 * +layout.server.ts, and accessed via $page.data.user in components.
 *
 * IMPORTANT: This module does NOT manage tokens or localStorage.
 * Authentication is handled server-side via HTTP-only session cookies.
 */

import type { UserRole } from './types';

// User type matching what's provided by the server
export interface User {
	id: number;
	email: string;
	name?: string;
	role: string;
	avatar_url?: string | null;
}

/**
 * Check if user has one of the specified roles.
 */
export function hasRole(user: User | null, roles: UserRole[]): boolean {
	return user ? roles.includes(user.role as UserRole) : false;
}

/**
 * Check if user is admin.
 */
export function isAdmin(user: User | null): boolean {
	return hasRole(user, ['admin']);
}

/**
 * Check if user can edit (admin or editor).
 */
export function canEdit(user: User | null): boolean {
	return hasRole(user, ['admin', 'editor']);
}

/**
 * Get auth state helpers from a user object.
 * Use with $page.data.user from +layout.server.ts.
 *
 * Example:
 *   import { page } from '$app/stores';
 *   import { getAuthHelpers } from '$lib/auth.svelte';
 *   const auth = getAuthHelpers($page.data.user);
 */
export function getAuthHelpers(user: User | null) {
	return {
		user,
		isAuthenticated: !!user,
		isAdmin: isAdmin(user),
		canEdit: canEdit(user)
	};
}

// =============================================================================
// DEPRECATED - Legacy exports for backwards compatibility during migration
// These will be removed in a future version. Use getAuthHelpers() instead.
// =============================================================================

// Deprecated: Use $page.data.user instead
let _legacyUser = $state<User | null>(null);
let _isInitialized = $state(false);

/**
 * @deprecated Use $page.data.user from +layout.server.ts instead.
 * This function is kept for backwards compatibility.
 */
export function initAuth(): void {
	_isInitialized = true;
}

/**
 * @deprecated Use server actions instead of client-side token management.
 */
export function setAuth(userData: User, _tokens: unknown): void {
	_legacyUser = userData;
	_isInitialized = true;
}

/**
 * @deprecated Use $page.data.user instead.
 */
export function updateUser(userData: User): void {
	_legacyUser = userData;
}

/**
 * @deprecated Navigate to /logout instead.
 */
export function clearAuth(): void {
	_legacyUser = null;
}

/**
 * @deprecated Token management is now handled server-side.
 */
export function getAccessToken(): string | null {
	return null;
}

/**
 * @deprecated Token management is now handled server-side.
 */
export function getRefreshToken(): string | null {
	return null;
}

/**
 * @deprecated Token management is now handled server-side.
 */
export function updateAccessToken(_token: string): void {
	// No-op: tokens are managed server-side
}

/**
 * @deprecated Use getAuthHelpers($page.data.user) instead.
 */
export function getAuthState() {
	return {
		get user() {
			return _legacyUser;
		},
		get isLoading() {
			return !_isInitialized;
		},
		get isInitialized() {
			return _isInitialized;
		},
		get isAuthenticated() {
			return !!_legacyUser;
		},
		get isAdmin() {
			return _legacyUser?.role === 'admin';
		},
		get canEdit() {
			return _legacyUser?.role === 'admin' || _legacyUser?.role === 'editor';
		}
	};
}

/**
 * @deprecated Use getAuthHelpers($page.data.user) instead.
 */
export function isAuthenticated(): boolean {
	return !!_legacyUser;
}
