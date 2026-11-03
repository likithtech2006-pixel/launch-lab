// A Redis-backed job queue with cron scheduling.
const Redis = require("ioredis");
const redis = new Redis(process.env.REDIS_URL);
module.exports.schedule = (cron, job) => redis.zadd("nexus:jobs", Date.now(), JSON.stringify({ cron, job }));
