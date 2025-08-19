import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { eventService } from "@/services/eventService";
import { EventCard } from "@/components/EventCard";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Loader2, Users, Award, BookOpen } from "lucide-react";

export function HomePage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: events = [], isLoading, error } = useQuery({
    queryKey: ["/api/events", searchQuery],
    queryFn: () => eventService.getEvents({ search: searchQuery || undefined }),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchTerm);
  };

  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <section className="gradient-primary text-white relative overflow-hidden">
        <div className="absolute inset-0">
          <img 
            src="/hero-conference.svg" 
            alt="CDPI Pharma Conference" 
            className="w-full h-full object-cover opacity-20"
          />
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 relative z-10">
          <div className="text-center">
            <div className="mb-8">
              <img 
                src="/cdpi-logo.svg" 
                alt="CDPI Pharma Pass" 
                className="h-16 mx-auto mb-6"
              />
            </div>
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Encontre os Melhores Eventos
            </h1>
            <p className="text-xl md:text-2xl mb-8 text-primary-100">
              Descubra, compre e viva experiências incríveis
            </p>
            
            <div className="max-w-md mx-auto">
              <form onSubmit={handleSearch} className="relative">
                <Input
                  type="text"
                  placeholder="Buscar eventos..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full px-4 py-3 pr-12 rounded-lg text-slate-900 focus:outline-none focus:ring-4 focus:ring-primary-300"
                />
                <Button
                  type="submit"
                  size="sm"
                  className="absolute right-2 top-2 p-2 text-primary-600 hover:text-primary-700 bg-transparent hover:bg-transparent"
                >
                  <Search className="h-4 w-4" />
                </Button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* Events Section */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              {searchQuery ? `Resultados para "${searchQuery}"` : "Próximos Eventos"}
            </h2>
            <p className="text-lg text-slate-600">
              {searchQuery ? "Encontramos os melhores eventos para você" : "Não perca as melhores experiências"}
            </p>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="flex justify-center items-center py-16">
              <Loader2 className="h-12 w-12 animate-spin text-primary-600" />
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="text-center py-16">
              <p className="text-slate-600">
                Erro ao carregar eventos. Tente novamente mais tarde.
              </p>
            </div>
          )}

          {/* Events Grid */}
          {!isLoading && !error && (
            <>
              {events.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                  {events.map((event) => (
                    <EventCard key={event.id} event={event} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-16">
                  <p className="text-slate-600">
                    {searchQuery 
                      ? "Nenhum evento encontrado para sua busca."
                      : "Nenhum evento disponível no momento."
                    }
                  </p>
                  {searchQuery && (
                    <Button
                      onClick={() => {
                        setSearchQuery("");
                        setSearchTerm("");
                      }}
                      variant="outline"
                      className="mt-4"
                    >
                      Ver todos os eventos
                    </Button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </main>
  );
}
