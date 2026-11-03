export async function retry(fn, { attempts = 3, base = 100 } = {}) {
  for (let i = 0; ; i++) {
    try { return await fn(); } catch (e) {
      if (i >= attempts - 1) throw e;
      await new Promise((r) => setTimeout(r, base * 2 ** i));
    }
  }
}
