import { useState } from "react";
import { useParams, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { eventService } from "@/services/eventService";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CalendarDays, Clock, MapPin, Users, Minus, Plus } from "lucide-react";
import { TicketClass } from "@/types";

interface SelectedTicket {
  ticket_class_id: string;
  quantity: number;
}

export function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [, setLocation] = useLocation();
  const { isAuthenticated } = useAuth();
  const [selectedTickets, setSelectedTickets] = useState<SelectedTicket[]>([]);

  const { data: event, isLoading, error } = useQuery({
    queryKey: ["/api/events", id],
    queryFn: () => eventService.getEvent(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-4">Evento não encontrado</h1>
          <Button onClick={() => setLocation("/")}>
            Voltar para eventos
          </Button>
        </div>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  };

  const formatTime = (dateString: string) => {
    const start = new Date(dateString);
    const end = event.end ? new Date(event.end) : null;
    
    if (end) {
      return `${start.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })} - ${end.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
    }
    
    return start.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  };

  const getTicketQuantity = (ticketClassId: string) => {
    const selectedTicket = selectedTickets.find(item => item.ticket_class_id === ticketClassId);
    return selectedTicket ? selectedTicket.quantity : 0;
  };

  const updateTicketQuantity = (ticketClass: TicketClass, newQuantity: number) => {
    if (newQuantity < 0) return;

    setSelectedTickets(prevTickets => {
      const existingIndex = prevTickets.findIndex(item => item.ticket_class_id === ticketClass.id);
      
      if (newQuantity === 0) {
        // Remove item
        return prevTickets.filter(item => item.ticket_class_id !== ticketClass.id);
      }

      if (existingIndex >= 0) {
        // Update existing item
        const newTickets = [...prevTickets];
        newTickets[existingIndex] = {
          ...newTickets[existingIndex],
          quantity: newQuantity,
        };
        return newTickets;
      } else {
        // Add new item
        return [...prevTickets, {
          ticket_class_id: ticketClass.id,
          quantity: newQuantity,
        }];
      }
    });
  };

  const getTotalAmount = () => {
    return selectedTickets.reduce((total, item) => {
      const ticketClass = event.ticket_classes?.find(tc => tc.id === item.ticket_class_id);
      return total + (Number(ticketClass?.price) || 0) * item.quantity;
    }, 0);
  };

  const getTotalQuantity = () => {
    return selectedTickets.reduce((total, item) => total + item.quantity, 0);
  };

  const handleBuyTickets = () => {
    if (!isAuthenticated) {
      setLocation("/login");
      return;
    }

    if (getTotalQuantity() === 0) {
      return;
    }

    // Create URL params for checkout with selected tickets
    const params = new URLSearchParams();
    params.set('event_id', event.id);
    
    selectedTickets.forEach((ticket, index) => {
      params.set(`ticket_${index}_class_id`, ticket.ticket_class_id);
      params.set(`ticket_${index}_quantity`, ticket.quantity.toString());
    });
    
    setLocation(`/checkout?${params.toString()}`);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb */}
        <nav className="flex mb-8" aria-label="Breadcrumb">
          <ol className="flex items-center space-x-4">
            <li>
              <button 
                onClick={() => setLocation("/")}
                className="text-slate-500 hover:text-slate-700"
              >
                Eventos
              </button>
            </li>
            <li>
              <span className="text-slate-400 mx-2">/</span>
            </li>
            <li className="text-slate-900 font-medium truncate">
              {event.name}
            </li>
          </ol>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2">
            <Card className="mb-8">
              {event.image && (
                <img 
                  src={event.image} 
                  alt={event.name}
                  className="w-full h-80 object-cover rounded-t-xl"
                />
              )}
              
              <CardContent className="p-8">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-4">
                    <span className="bg-primary-100 text-primary-800 px-3 py-1 rounded-full text-sm font-medium">
                      Tecnologia
                    </span>
                    <span className="text-slate-500 text-sm">
                      {event.city}
                    </span>
                  </div>
                </div>
                
                <h1 className="text-3xl font-bold text-slate-900 mb-4">
                  {event.name}
                </h1>
                
                {/* Event Meta Information */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                  <div className="flex items-center">
                    <CalendarDays className="text-primary-600 mr-3 h-5 w-5" />
                    <div>
                      <p className="text-sm text-slate-500">Data</p>
                      <p className="font-medium">{formatDate(event.start)}</p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    <Clock className="text-primary-600 mr-3 h-5 w-5" />
                    <div>
                      <p className="text-sm text-slate-500">Horário</p>
                      <p className="font-medium">{formatTime(event.start)}</p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    <MapPin className="text-primary-600 mr-3 h-5 w-5" />
                    <div>
                      <p className="text-sm text-slate-500">Local</p>
                      <p className="font-medium">{event.location}</p>
                    </div>
                  </div>
                </div>

                {/* Event Description */}
                {event.description && (
                  <div className="mb-8">
                    <h2 className="text-xl font-bold text-slate-900 mb-4">Sobre o Evento</h2>
                    <div className="prose prose-slate max-w-none">
                      <p>{event.description}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar - Ticket Selection */}
          <div className="lg:col-span-1">
            <Card className="sticky top-24">
              <CardContent className="p-6">
                <h3 className="text-xl font-bold text-slate-900 mb-6">
                  Selecione seus Ingressos
                </h3>
                
                {/* Ticket Classes */}
                {event.ticket_classes && event.ticket_classes.length > 0 ? (
                  <div className="space-y-4 mb-6">
                    {event.ticket_classes.map((ticketClass) => (
                      <div 
                        key={ticketClass.id}
                        className="border border-slate-200 rounded-lg p-4 hover:border-primary-300 transition-colors"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h4 className="font-medium text-slate-900">
                              {ticketClass.name}
                            </h4>
                            {ticketClass.description && (
                              <p className="text-sm text-slate-600">
                                {ticketClass.description}
                              </p>
                            )}
                          </div>
                          <span className="text-lg font-bold text-primary-600">
                            R$ {Number(ticketClass.price).toFixed(2).replace(".", ",")}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-500">
                            Disponível
                          </span>
                          <div className="flex items-center space-x-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => updateTicketQuantity(
                                ticketClass, 
                                getTicketQuantity(ticketClass.id) - 1
                              )}
                              disabled={getTicketQuantity(ticketClass.id) === 0}
                              className="w-8 h-8 p-0"
                            >
                              <Minus className="h-4 w-4" />
                            </Button>
                            <span className="w-8 text-center font-medium">
                              {getTicketQuantity(ticketClass.id)}
                            </span>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => updateTicketQuantity(
                                ticketClass, 
                                getTicketQuantity(ticketClass.id) + 1
                              )}
                              className="w-8 h-8 p-0"
                            >
                              <Plus className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-slate-600">
                      Nenhum ingresso disponível para este evento.
                    </p>
                  </div>
                )}

                {/* Order Summary */}
                <div className="border-t border-slate-200 pt-4 mb-6">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-slate-600">Subtotal</span>
                    <span className="font-medium">
                      R$ {getTotalAmount().toFixed(2).replace(".", ",")}
                    </span>
                  </div>
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-slate-600">Taxa de serviço</span>
                    <span className="font-medium">R$ 0,00</span>
                  </div>
                  <div className="flex justify-between items-center text-lg font-bold">
                    <span>Total</span>
                    <span className="text-primary-600">
                      R$ {getTotalAmount().toFixed(2).replace(".", ",")}
                    </span>
                  </div>
                </div>

                {/* Purchase Button */}
                <Button 
                  onClick={handleBuyTickets}
                  disabled={getTotalQuantity() === 0}
                  className="w-full bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {!isAuthenticated 
                    ? "Fazer Login para Comprar" 
                    : getTotalQuantity() === 0 
                      ? "Selecione Ingressos"
                      : "Comprar Ingressos"
                  }
                </Button>

                <p className="text-xs text-slate-500 text-center mt-4">
                  Pagamento seguro via PIX, cartão ou boleto
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
