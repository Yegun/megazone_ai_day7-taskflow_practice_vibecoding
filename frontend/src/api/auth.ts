import type { User } from '../types'
import { request } from './tasks'

export function getMe(): Promise<User> {
  return request('/api/auth/me')
}

export function login(username: string, password: string): Promise<User> {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function register(username: string, password: string): Promise<User> {
  return request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logout(): Promise<void> {
  return request('/api/auth/logout', { method: 'POST' })
}
