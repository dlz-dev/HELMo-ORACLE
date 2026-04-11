import { SourcesGrid } from "@/components/sources/SourcesGrid";

export default function SourcesPage() {
  return (
    <div className="max-w-5xl mx-auto p-6 py-12">
      <div className="text-center mb-12 space-y-2">
        <h1 className="text-3xl font-oracle font-semibold text-gold tracking-widest uppercase">
          Librairie
        </h1>
        <p className="text-sm text-muted-fg">
          Consultez et explorez l'ensemble des archives ingérées par Oracle
        </p>
      </div>
      <SourcesGrid />
    </div>
  );
}
