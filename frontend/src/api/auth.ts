const TOKEN_KEY = 'gallaia.operatorToken'

export function getOperatorToken(): string {
  const stored = sessionStorage.getItem(TOKEN_KEY)?.trim()
  if (stored) return stored

  const entered = window.prompt('Introduce el token de operador de GallaIA')
  const token = entered?.trim() ?? ''
  if (token) sessionStorage.setItem(TOKEN_KEY, token)
  return token
}

export function clearOperatorToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}

export function authHeaders(): Record<string, string> {
  const token = getOperatorToken()
  return { Authorization: `Bearer ${token}` }
}

export async function authFetch(
  input: string,
  init?: RequestInit,
): Promise<Response> {
  const withAuth = (token: string): RequestInit => {
    const headers = new Headers(init?.headers)
    headers.set('Authorization', `Bearer ${token}`)
    return { ...init, headers }
  }

  let response = await fetch(input, withAuth(getOperatorToken()))
  if (response.status === 401) {
    clearOperatorToken()
    response = await fetch(input, withAuth(getOperatorToken()))
  }
  return response
}
