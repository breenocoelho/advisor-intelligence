import { auth } from "@clerk/nextjs/server";
import AtivosBoard from "./AtivosBoard";

type Asset = {
  id: string;
  name: string;
  asset_class: string;
  issuer: string | null;
  risk_rating: string | null;
  due_date: string | null;
  total_exposure: number;
  client_count: number;
};

async function getAssets(): Promise<Asset[]> {
  const { getToken } = await auth();
  const token = await getToken();

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/assets/`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  if (!res.ok) return [];
  return res.json();
}

export default async function AtivosPage() {
  const assets = await getAssets();

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 sm:py-14">
      <header className="mb-8 flex items-end justify-between border-b border-[#14181F]/10 pb-6">
        <div>
          <p className="text-sm text-[#14181F]/50">Cadastro de instrumentos</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight">Ativos</h1>
        </div>
        <div className="text-right">
          <p className="font-mono text-2xl font-semibold tabular-nums">{assets.length}</p>
          <p className="text-sm text-[#14181F]/50">{assets.length === 1 ? "ativo" : "ativos"}</p>
        </div>
      </header>

      {assets.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#14181F]/15 py-16 text-center">
          <p className="text-lg font-medium">Nenhum ativo sincronizado.</p>
        </div>
      ) : (
        <AtivosBoard assets={assets} />
      )}
    </main>
  );
}
