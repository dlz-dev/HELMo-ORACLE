import { AdminPanel } from "@/components/admin/AdminPanel";

export default function AdminPage() {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-oracle text-gold mb-6 text-center">
        Administration Oracle
      </h1>
      <AdminPanel />
    </div>
  );
}
