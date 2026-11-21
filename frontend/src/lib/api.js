import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const getMeta = () => axios.get(`${API}/meta`).then((r) => r.data);

export const getDashboard = ({ start, end, carrier, region }) => {
  const params = new URLSearchParams();
  if (start) params.append("start", start);
  if (end) params.append("end", end);
  if (carrier && carrier !== "all") params.append("carrier", carrier);
  if (region && region !== "all") params.append("region", region);
  return axios.get(`${API}/dashboard?${params}`).then((r) => r.data);
};

export const getForecast = (body) => axios.post(`${API}/forecast`, body).then((r) => r.data);

export async function askStream(question, onEvent) {
  const res = await fetch(`${API}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop();
    for (const p of parts) {
      const line = p.trim();
      if (line.startsWith("data:")) onEvent(JSON.parse(line.slice(5)));
    }
  }
}
