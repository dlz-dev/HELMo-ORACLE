import { ChatInterface } from "@/components/chat/ChatInterface";

export default function HomePage() {
  return (
    <div className="h-[calc(100vh-64px)] w-full">
      {" "}
      {/* Ajustez la hauteur selon votre Navbar */}
      <ChatInterface />
    </div>
  );
}
