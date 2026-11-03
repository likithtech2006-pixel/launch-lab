export default function Page() {
  const db = process.env.DATABASE_URL;
  return <main>Pinboard Lite {db ? "connected" : "no database"}</main>;
}
