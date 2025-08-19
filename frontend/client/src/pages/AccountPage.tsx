import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { orderService } from "@/services/orderService";
import { useAuth } from "@/hooks/useAuth";
import { TicketAssignmentModal } from "@/components/TicketAssignmentModal";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { User, ShoppingBag, Settings, CalendarDays, Download, AlertTriangle } from "lucide-react";
import { Ticket, Order } from "@/types";

export function AccountPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("orders");
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [assignmentModalOpen, setAssignmentModalOpen] = useState(false);

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["/api/orders"],
    queryFn: () => orderService.getOrders(),
  });

  const handleAssignTicket = (ticket: Ticket) => {
    setSelectedTicket(ticket);
    setAssignmentModalOpen(true);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pago":
        return "bg-green-100 text-green-800";
      case "pendente":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-slate-100 text-slate-800";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "pago":
        return "Pago";
      case "pendente":
        return "Pendente";
      default:
        return status;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("pt-BR");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Account Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Minha Conta</h1>
          <p className="text-slate-600">Gerencie seus dados e acompanhe seus pedidos</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar Navigation */}
          <div className="lg:col-span-1">
            <Card>
              <CardContent className="p-6">
                <div className="text-center mb-6">
                  <Avatar className="w-20 h-20 mx-auto mb-4">
                    <AvatarFallback className="text-lg">
                      {user?.full_name?.split(" ").map(n => n[0]).join("").slice(0, 2)}
                    </AvatarFallback>
                  </Avatar>
                  <h3 className="font-medium text-slate-900">{user?.full_name}</h3>
                  <p className="text-sm text-slate-600">{user?.email}</p>
                </div>
                
                <nav className="space-y-2">
                  <Button
                    variant={activeTab === "profile" ? "default" : "ghost"}
                    onClick={() => setActiveTab("profile")}
                    className="w-full justify-start"
                  >
                    <User className="mr-3 h-4 w-4" />
                    Perfil
                  </Button>
                  <Button
                    variant={activeTab === "orders" ? "default" : "ghost"}
                    onClick={() => setActiveTab("orders")}
                    className="w-full justify-start"
                  >
                    <ShoppingBag className="mr-3 h-4 w-4" />
                    Meus Pedidos
                  </Button>
                  <Button
                    variant={activeTab === "settings" ? "default" : "ghost"}
                    onClick={() => setActiveTab("settings")}
                    className="w-full justify-start"
                  >
                    <Settings className="mr-3 h-4 w-4" />
                    Configurações
                  </Button>
                </nav>
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {activeTab === "orders" && (
              <div className="space-y-6">
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h2 className="text-xl font-bold text-slate-900">Meus Pedidos</h2>
                      <div className="flex space-x-2">
                        <Button size="sm" variant="default">
                          Todos
                        </Button>
                        <Button size="sm" variant="outline">
                          Pagos
                        </Button>
                        <Button size="sm" variant="outline">
                          Pendentes
                        </Button>
                      </div>
                    </div>

                    {orders.length === 0 ? (
                      <div className="text-center py-16">
                        <ShoppingBag className="mx-auto h-12 w-12 text-slate-400 mb-4" />
                        <p className="text-slate-600">Você ainda não fez nenhum pedido.</p>
                        <Button className="mt-4" onClick={() => window.location.href = "/"}>
                          Ver Eventos
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {orders.map((order: Order) => (
                          <Card key={order.id} className="border border-slate-200">
                            <CardContent className="p-6">
                              <div className="flex flex-col md:flex-row md:items-center justify-between mb-4">
                                <div>
                                  <h3 className="font-medium text-slate-900 mb-1">
                                    {order.items?.[0]?.event?.name || "Evento"}
                                  </h3>
                                  <p className="text-sm text-slate-600">
                                    Pedido <span className="font-mono">#{order.id.slice(-8)}</span> • {formatDate(order.created_at)}
                                  </p>
                                </div>
                                <div className="flex items-center space-x-4 mt-4 md:mt-0">
                                  <Badge className={getStatusColor(order.status)}>
                                    {getStatusText(order.status)}
                                  </Badge>
                                  <span className="font-bold text-slate-900">
                                    R$ {order.total_amount.toFixed(2).replace(".", ",")}
                                  </span>
                                </div>
                              </div>

                              {/* Tickets in this order */}
                              {order.tickets && order.tickets.length > 0 && (
                                <div className="space-y-3 mb-4">
                                  {order.tickets.map((ticket) => (
                                    <div key={ticket.id} className="bg-slate-50 rounded-lg p-4">
                                      <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                          <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm font-medium text-slate-900">
                                              {ticket.order_item?.ticket_class?.name || "Ingresso"}
                                            </span>
                                            <span className="text-sm text-slate-600">
                                              R$ {ticket.order_item?.unit_price?.toFixed(2).replace(".", ",")}
                                            </span>
                                          </div>
                                          
                                          <div className="flex items-center justify-between">
                                            <div className="text-sm text-slate-600">
                                              {ticket.holder_name && ticket.holder_email ? (
                                                <>
                                                  <span className="font-medium">{ticket.holder_name}</span>
                                                  <span className="text-xs block">{ticket.holder_email}</span>
                                                </>
                                              ) : (
                                                <span className="text-amber-600 font-medium flex items-center">
                                                  <AlertTriangle className="h-4 w-4 mr-1" />
                                                  Ingresso não atribuído
                                                </span>
                                              )}
                                            </div>
                                            
                                            <div className="flex items-center space-x-2">
                                              {ticket.holder_name && ticket.holder_email ? (
                                                <>
                                                  <Badge className="bg-green-100 text-green-800 text-xs">
                                                    ✓ Atribuído
                                                  </Badge>
                                                  <Button size="sm" variant="ghost">
                                                    <Download className="h-4 w-4" />
                                                  </Button>
                                                </>
                                              ) : (
                                                <Button
                                                  size="sm"
                                                  onClick={() => handleAssignTicket(ticket)}
                                                  className="bg-primary-600 text-white hover:bg-primary-700"
                                                >
                                                  Atribuir Ingresso
                                                </Button>
                                              )}
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Order status specific actions */}
                              <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                                <div className="text-sm text-slate-600 flex items-center">
                                  <CalendarDays className="h-4 w-4 mr-1" />
                                  <span>
                                    {order.items?.[0]?.event?.start ? 
                                      new Date(order.items[0].event.start).toLocaleDateString("pt-BR", {
                                        day: "2-digit",
                                        month: "long",
                                        year: "numeric",
                                        hour: "2-digit",
                                        minute: "2-digit"
                                      }) : 
                                      "Data não informada"
                                    }
                                  </span>
                                </div>
                                <div className="flex space-x-2">
                                  {order.status === "pendente" && (
                                    <Button size="sm" className="bg-primary-600 hover:bg-primary-700">
                                      Completar Pagamento
                                    </Button>
                                  )}
                                  <Button size="sm" variant="outline">
                                    Ver Detalhes
                                  </Button>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === "profile" && (
              <Card>
                <CardContent className="p-6">
                  <h2 className="text-xl font-bold text-slate-900 mb-6">Perfil</h2>
                  <div className="space-y-4">
                    <p className="text-slate-600">Funcionalidade de edição de perfil em desenvolvimento.</p>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === "settings" && (
              <Card>
                <CardContent className="p-6">
                  <h2 className="text-xl font-bold text-slate-900 mb-6">Configurações</h2>
                  <div className="space-y-4">
                    <p className="text-slate-600">Configurações em desenvolvimento.</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      <TicketAssignmentModal
        ticket={selectedTicket}
        isOpen={assignmentModalOpen}
        onClose={() => {
          setAssignmentModalOpen(false);
          setSelectedTicket(null);
        }}
      />
    </div>
  );
}
