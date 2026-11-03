# tinyretry

Retry any async function with exponential backoff. 600 bytes, zero dependencies.

```js
import { retry } from "tinyretry";

const data = await retry(() => fetch("https://api.example.com"), { attempts: 5 });
```

## Install

```bash
npm install tinyretry
```
