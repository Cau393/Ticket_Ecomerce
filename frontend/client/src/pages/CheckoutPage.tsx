import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useMutation } from "@tanstack/react-query";
import { orderService } from "@/services/orderService";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { CreditCard, QrCode, FileText } from "lucide-react";

const holderSchema = z.object({
  holder_name: z.string().min(1, "Nome é obrigatório"),
  holder_email: z.string().email("Email inválido"),
});

const checkoutSchema = z.object({
  payment_method: z.enum(["PIX", "CREDIT_CARD", "BOLETO"]),
  terms_accepted: z.boolean().refine(val => val === true, "Aceite os termos para continuar"),
  holders: z.array(holderSchema),
});

type CheckoutFormData = z.infer<typeof checkoutSchema>;

export function CheckoutPage() {
  const [, setLocation] = useLocation();
  const { user } = useAuth();
  const { toast } = useToast();
  const [checkoutData, setCheckoutData] = useState<any>(null);

  const form = useForm<CheckoutFormData>({
    resolver: zodResolver(checkoutSchema),
    defaultValues: {
      payment_method: "PIX",
      terms_accepted: false,
      holders: [],
    },
  });

  useEffect(() => {
    const stored = localStorage.getItem("checkout_cart");
    if (!stored) {
      setLocation("/");
      return;
    }

    const data = JSON.parse(stored);
    setCheckoutData(data);

    // Initialize holder forms
    const allHolders = data.items.flatMap((item: any) => item.holders);
    form.setValue("holders", allHolders);
  }, [form, setLocation]);

  const createOrderMutation = useMutation({
    mutationFn: (formData: CheckoutFormData) => {
      if (!checkoutData) throw new Error("No checkout data");

      // Map form holders back to items structure
      let holderIndex = 0;
      const itemsWithHolders = checkoutData.items.map((item: any) => ({
        ticket_class_id: item.ticket_class_id,
        quantity: item.quantity,
        holders: formData.holders.slice(holderIndex, holderIndex += item.quantity),
      }));

      return orderService.createOrder({
        items: itemsWithHolders,
        billing_type: formData.payment_method,
      });
    },
    onSuccess: (order) => {
      localStorage.removeItem("checkout_cart");
      localStorage.setItem("order_data", JSON.stringify(order));
      
      toast({
        title: "Pedido criado com sucesso!",
        description: "Finalize o pagamento para garantir seus ingressos.",
      });
      
      setLocation("/payment-confirmation");
    },
    onError: (error) => {
      toast({
        title: "Erro ao processar pedido",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const onSubmit = (data: CheckoutFormData) => {
    createOrderMutation.mutate(data);
  };

  if (!checkoutData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const getTotalAmount = () => {
    return checkoutData.items.reduce((total: number, item: any) => {
      const ticketClass = checkoutData.event.ticket_classes?.find((tc: any) => tc.id === item.ticket_class_id);
      return total + (ticketClass?.price || 0) * item.quantity;
    }, 0);
  };

  let holderIndex = 0;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Finalizar Compra</h1>
          <p className="text-slate-600">Complete os dados para finalizar sua compra</p>
        </div>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Main Checkout Form */}
              <div className="lg:col-span-2 space-y-8">
                
                {/* Ticket Holder Forms */}
                {checkoutData.items.map((item: any, itemIndex: number) => {
                  const ticketClass = checkoutData.event.ticket_classes?.find((tc: any) => tc.id === item.ticket_class_id);
                  
                  return Array.from({ length: item.quantity }).map((_, ticketIndex) => {
                    const currentHolderIndex = holderIndex++;
                    
                    return (
                      <Card key={`${itemIndex}-${ticketIndex}`}>
                        <CardContent className="p-6">
                          <h3 className="text-xl font-bold text-slate-900 mb-6">
                            Dados do Participante{" "}
                            <span className="text-primary-600">#{currentHolderIndex + 1}</span>
                          </h3>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <FormField
                              control={form.control}
                              name={`holders.${currentHolderIndex}.holder_name`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>Nome Completo *</FormLabel>
                                  <FormControl>
                                    <Input placeholder="Digite o nome completo" {...field} />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />

                            <FormField
                              control={form.control}
                              name={`holders.${currentHolderIndex}.holder_email`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>E-mail *</FormLabel>
                                  <FormControl>
                                    <Input 
                                      type="email" 
                                      placeholder="exemplo@email.com" 
                                      {...field} 
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>
                          
                          {/* Ticket Details */}
                          <div className="mt-6 p-4 bg-slate-50 rounded-lg">
                            <div className="flex justify-between items-center">
                              <div>
                                <p className="font-medium text-slate-900">
                                  {checkoutData.event.name}
                                </p>
                                <p className="text-sm text-slate-600">
                                  {ticketClass?.name}
                                </p>
                              </div>
                              <span className="font-bold text-primary-600">
                                R$ {ticketClass?.price.toFixed(2).replace(".", ",")}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  });
                })}

                {/* Payment Method Selection */}
                <Card>
                  <CardContent className="p-6">
                    <h3 className="text-xl font-bold text-slate-900 mb-6">Forma de Pagamento</h3>
                    
                    <FormField
                      control={form.control}
                      name="payment_method"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <RadioGroup
                              onValueChange={field.onChange}
                              defaultValue={field.value}
                              className="space-y-4"
                            >
                              <div className="flex items-center space-x-3 p-4 border border-slate-200 rounded-lg hover:border-primary-300">
                                <RadioGroupItem value="PIX" id="pix" />
                                <QrCode className="text-primary-600 h-5 w-5" />
                                <div>
                                  <Label htmlFor="pix" className="font-medium text-slate-900">PIX</Label>
                                  <p className="text-sm text-slate-600">Pagamento instantâneo</p>
                                </div>
                              </div>

                              <div className="flex items-center space-x-3 p-4 border border-slate-200 rounded-lg hover:border-primary-300">
                                <RadioGroupItem value="CREDIT_CARD" id="credit" />
                                <CreditCard className="text-primary-600 h-5 w-5" />
                                <div>
                                  <Label htmlFor="credit" className="font-medium text-slate-900">Cartão de Crédito</Label>
                                  <p className="text-sm text-slate-600">Parcelamento disponível</p>
                                </div>
                              </div>

                              <div className="flex items-center space-x-3 p-4 border border-slate-200 rounded-lg hover:border-primary-300">
                                <RadioGroupItem value="BOLETO" id="boleto" />
                                <FileText className="text-primary-600 h-5 w-5" />
                                <div>
                                  <Label htmlFor="boleto" className="font-medium text-slate-900">Boleto Bancário</Label>
                                  <p className="text-sm text-slate-600">Vencimento em 3 dias úteis</p>
                                </div>
                              </div>
                            </RadioGroup>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </CardContent>
                </Card>
              </div>

              {/* Order Summary Sidebar */}
              <div className="lg:col-span-1">
                <Card className="sticky top-24">
                  <CardContent className="p-6">
                    <h3 className="text-xl font-bold text-slate-900 mb-6">Resumo do Pedido</h3>
                    
                    {/* Event Info */}
                    <div className="mb-6">
                      <h4 className="font-medium text-slate-900 mb-2">
                        {checkoutData.event.name}
                      </h4>
                      <p className="text-sm text-slate-600">
                        {new Date(checkoutData.event.start).toLocaleDateString("pt-BR")} • {checkoutData.event.city}
                      </p>
                    </div>

                    {/* Ticket Breakdown */}
                    <div className="space-y-3 mb-6">
                      {checkoutData.items.map((item: any, index: number) => {
                        const ticketClass = checkoutData.event.ticket_classes?.find((tc: any) => tc.id === item.ticket_class_id);
                        return (
                          <div key={index} className="flex justify-between items-center">
                            <div>
                              <p className="text-sm font-medium text-slate-900">
                                {item.quantity}x {ticketClass?.name}
                              </p>
                            </div>
                            <span className="text-sm font-medium">
                              R$ {((ticketClass?.price || 0) * item.quantity).toFixed(2).replace(".", ",")}
                            </span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Price Breakdown */}
                    <div className="border-t border-slate-200 pt-4 space-y-2 mb-6">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Subtotal</span>
                        <span>R$ {getTotalAmount().toFixed(2).replace(".", ",")}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Taxa de serviço</span>
                        <span>R$ 0,00</span>
                      </div>
                      <div className="flex justify-between text-lg font-bold pt-2 border-t border-slate-200">
                        <span>Total</span>
                        <span className="text-primary-600">
                          R$ {getTotalAmount().toFixed(2).replace(".", ",")}
                        </span>
                      </div>
                    </div>

                    {/* Terms and Conditions */}
                    <div className="mb-6">
                      <FormField
                        control={form.control}
                        name="terms_accepted"
                        render={({ field }) => (
                          <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                            <FormControl>
                              <Checkbox
                                checked={field.value}
                                onCheckedChange={field.onChange}
                              />
                            </FormControl>
                            <div className="space-y-1 leading-none">
                              <FormLabel className="text-xs text-slate-600">
                                Concordo com os{" "}
                                <a href="#" className="text-primary-600 hover:underline">
                                  termos de uso
                                </a>{" "}
                                e{" "}
                                <a href="#" className="text-primary-600 hover:underline">
                                  política de privacidade
                                </a>
                              </FormLabel>
                              <FormMessage />
                            </div>
                          </FormItem>
                        )}
                      />
                    </div>

                    {/* Checkout Button */}
                    <Button 
                      type="submit"
                      disabled={createOrderMutation.isPending}
                      className="w-full bg-primary-600 text-white hover:bg-primary-700"
                    >
                      {createOrderMutation.isPending ? "Processando..." : "Finalizar Compra"}
                    </Button>

                    {/* Security Notice */}
                    <div className="mt-4 flex items-center justify-center text-xs text-slate-500">
                      <span>🔒 Pagamento 100% seguro</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
}
