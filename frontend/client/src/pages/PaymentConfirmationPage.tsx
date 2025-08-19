import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { orderService } from "@/services/orderService";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Check, Copy, QrCode } from "lucide-react";
import { Order } from "@/types";

export function PaymentConfirmationPage() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [orderData, setOrderData] = useState<Order | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("order_data");
    if (!stored) {
      setLocation("/");
      return;
    }

    const data = JSON.parse(stored);
    setOrderData(data);
  }, [setLocation]);

  const { data: updatedOrder, refetch } = useQuery({
    queryKey: ["/api/orders", orderData?.id],
    queryFn: () => orderService.getOrder(orderData!.id),
    enabled: !!orderData?.id,
    refetchInterval: orderData?.status === "pendente" ? 5000 : false, // Poll every 5 seconds if pending
  });

  const order = updatedOrder || orderData;

  useEffect(() => {
    if (updatedOrder && updatedOrder.status === "pago") {
      toast({
        title: "Pagamento confirmado!",
        description: "Seus ingressos foram enviados por email.",
      });
      localStorage.removeItem("order_data");
    }
  }, [updatedOrder, toast]);

  const copyPixCode = () => {
    if (order?.payment_data?.pixCode) {
      navigator.clipboard.writeText(order.payment_data.pixCode);
      toast({
        title: "Código PIX copiado!",
        description: "Cole o código no seu app de pagamentos.",
      });
    }
  };

  const checkPaymentStatus = () => {
    refetch();
  };

  const goToAccount = () => {
    setLocation("/account");
  };

  if (!order) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

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
        return "Aguardando Pagamento";
      default:
        return status;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <Card>
          <CardContent className="p-8 text-center">
            {/* Success Icon */}
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Check className="text-2xl text-green-600 h-8 w-8" />
            </div>

            <h1 className="text-2xl font-bold text-slate-900 mb-4">
              {order.status === "pago" ? "Pagamento Confirmado!" : "Pedido Confirmado!"}
            </h1>
            <p className="text-slate-600 mb-8">
              {order.status === "pago" 
                ? "Seus ingressos foram enviados por email."
                : "Seu pedido foi criado com sucesso. Complete o pagamento para garantir seus ingressos."
              }
            </p>

            {/* PIX Payment Section - Only show if status is pending and payment method is PIX */}
            {order.status === "pendente" && order.payment_data && (
              <div className="bg-slate-50 rounded-lg p-6 mb-8">
                <h3 className="text-lg font-bold text-slate-900 mb-4">Pagamento via PIX</h3>
                
                {/* QR Code Placeholder */}
                <div className="bg-white p-4 rounded-lg inline-block mb-4">
                  <div className="w-48 h-48 bg-slate-200 rounded-lg flex items-center justify-center mx-auto">
                    <QrCode className="text-6xl text-slate-400 h-16 w-16" />
                  </div>
                </div>

                {/* PIX Code */}
                {order.payment_data.pixCode && (
                  <div className="mb-4">
                    <Label className="block text-sm font-medium text-slate-700 mb-2">
                      Código PIX
                    </Label>
                    <div className="flex">
                      <Input 
                        value={order.payment_data.pixCode}
                        className="flex-1 bg-slate-50 text-xs font-mono"
                        readOnly
                      />
                      <Button 
                        onClick={copyPixCode}
                        className="ml-2 px-4 bg-primary-600 hover:bg-primary-700"
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}

                {/* Payment Instructions */}
                <div className="text-left">
                  <h4 className="font-medium text-slate-900 mb-2">Como pagar:</h4>
                  <ol className="text-sm text-slate-600 space-y-1 list-decimal list-inside">
                    <li>Abra o app do seu banco</li>
                    <li>Escaneie o QR Code ou cole o código PIX</li>
                    <li>Confirme o pagamento</li>
                    <li>Pronto! Você receberá os ingressos por e-mail</li>
                  </ol>
                </div>
              </div>
            )}

            {/* Order Details */}
            <div className="border-t border-slate-200 pt-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-slate-600">Pedido</span>
                <span className="font-mono text-sm">#{order.id.slice(-8)}</span>
              </div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-slate-600">Valor</span>
                <span className="font-bold text-primary-600">
                  R$ {order.total_amount.toFixed(2).replace(".", ",")}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Status</span>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                  {getStatusText(order.status)}
                </span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 mt-8">
              {order.status === "pendente" && (
                <Button 
                  onClick={checkPaymentStatus}
                  className="flex-1 bg-primary-600 text-white hover:bg-primary-700"
                >
                  Verificar Pagamento
                </Button>
              )}
              <Button 
                onClick={goToAccount}
                variant={order.status === "pendente" ? "outline" : "default"}
                className={order.status === "pendente" 
                  ? "flex-1" 
                  : "flex-1 bg-primary-600 text-white hover:bg-primary-700"
                }
              >
                Ver Meus Pedidos
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
