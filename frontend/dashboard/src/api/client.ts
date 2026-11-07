export async function api<T = unknown>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch('/api/v1' + url, options);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(typeof error.detail === 'string' ? error.detail : '请求参数或服务异常');
  }
  return response.json() as Promise<T>;
}
export const json = (method: string, data: unknown): RequestInit => ({
  method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
});
