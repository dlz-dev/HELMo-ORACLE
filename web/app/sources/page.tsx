import { SourcesGrid } from "@/components/sources/SourcesGrid";

export default function SourcesPage() {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-oracle text-gold mb-6 text-center">
        Sources de Connaissance
      </h1>
      <SourcesGrid />
    </div>
  );
}
