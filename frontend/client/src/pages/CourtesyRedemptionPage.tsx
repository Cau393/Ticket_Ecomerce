import { useState, useEffect } from "react";
import { useParams, useLocation } from "wouter";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Gift, CalendarDays, MapPin, Users } from "lucide-react";

interface CourtesyData {
  event: {
    id: string;
    name: string;
    start: string;
    location: string;
    city: string;
    description?: string;
  };
  quantity: number;
  partner_company: string;
  redemption_token: string;
}

export function CourtesyRedemptionPage() {
  const { token } = useParams<{ token: string }>();
  const [, setLocation] = useLocation();
  const { isAuthenticated, user } = useAuth();
  const { toast } = useToast();
  const [courtesyData, setCourtesyData] = useState<CourtesyData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCourtesyData = async () => {
      try {
        // In a real implementation, this would fetch courtesy order data
        // from the backend using the redemption token
        const response = await fetch(`/api/courtesy/${token}`);
        
        if (!response.ok) {
          throw new Error("Cortesia não encontrada ou expirada");
        }

        const data = await response.json();
        setCourtesyData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao carregar cortesia");
      } finally {
        setIsLoading(false);
      }
    };

    if (token) {
      fetchCourtesyData();
    } else {
      setError("Token de cortesia inválido");
      setIsLoading(false);
    }
  }, [token]);

  const handleClaimCourtesy = async () => {
    if (!isAuthenticated) {
      setLocation("/login");
      return;
    }

    try {
      // In a real implementation, this would claim the courtesy tickets
      // and assign them to the current user
      const response = await fetch(`/api/courtesy/${token}/claim`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      if (!response.ok) {
        throw new Error("Erro ao resgatar cortesia");
      }

      toast({
        title: "Cortesia resgatada com sucesso!",
        description: "Seus ingressos estão disponíveis na sua conta.",
      });

      setLocation("/account");
    } catch (error) {
      toast({
        title: "Erro ao resgatar cortesia",
        description: error instanceof Error ? error.message : "Tente novamente mais tarde",
        variant: "destructive",
      });
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error || !courtesyData) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <Card>
            <CardContent className="p-8 text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <Gift className="text-2xl text-red-600 h-8 w-8" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 mb-4">
                Cortesia não encontrada
              </h1>
              <p className="text-slate-600 mb-8">
                {error || "O link de cortesia não é válido ou já foi utilizado."}
              </p>
              <Button onClick={() => setLocation("/")}>
                Voltar para Eventos
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <Card>
          <CardContent className="p-8 text-center">
            {/* Gift Icon */}
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Gift className="text-2xl text-emerald-600 h-8 w-8" />
            </div>

            <h1 className="text-3xl font-bold text-slate-900 mb-4">
              Você ganhou ingressos!
            </h1>
            <p className="text-lg text-slate-600 mb-8">
              Sua empresa parceira ofereceu ingressos cortesia para este evento.
            </p>

            {/* Event Info */}
            <div className="bg-slate-50 rounded-lg p-6 mb-8">
              <h3 className="text-xl font-bold text-slate-900 mb-2">
                {courtesyData.event.name}
              </h3>
              <div className="flex items-center justify-center space-x-6 text-sm text-slate-600 mb-4">
                <div className="flex items-center">
                  <CalendarDays className="mr-2 h-4 w-4" />
                  <span>{formatDate(courtesyData.event.start)}</span>
                </div>
                <div className="flex items-center">
                  <MapPin className="mr-2 h-4 w-4" />
                  <span>{courtesyData.event.city}</span>
                </div>
              </div>
              
              <div className="mb-4">
                <p className="text-sm text-slate-600 mb-2">Local:</p>
                <p className="font-medium text-slate-900">{courtesyData.event.location}</p>
              </div>

              <div className="flex items-center justify-center">
                <span className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full text-sm font-medium flex items-center">
                  <Users className="mr-1 h-4 w-4" />
                  {courtesyData.quantity} {courtesyData.quantity === 1 ? "ingresso cortesia" : "ingressos cortesia"}
                </span>
              </div>
            </div>

            {/* Company Info */}
            <div className="mb-8">
              <p className="text-sm text-slate-600">Oferecido por:</p>
              <p className="text-lg font-medium text-primary-600">
                {courtesyData.partner_company}
              </p>
            </div>

            {/* Login Prompt or Claim Section */}
            {!isAuthenticated ? (
              <div className="mb-8">
                <p className="text-slate-600 mb-4">
                  Para resgatar seus ingressos, faça login ou crie uma conta:
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <Button 
                    onClick={() => setLocation("/login")}
                    className="bg-primary-600 text-white hover:bg-primary-700"
                  >
                    Fazer Login
                  </Button>
                  <Button 
                    onClick={() => setLocation("/register")}
                    variant="outline"
                  >
                    Criar Conta
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mb-8">
                <p className="text-slate-600 mb-6">
                  Olá, <strong>{user?.full_name}</strong>! Clique no botão abaixo para resgatar seus ingressos.
                </p>
                <Button 
                  onClick={handleClaimCourtesy}
                  className="bg-emerald-600 text-white hover:bg-emerald-700 text-lg px-8 py-4"
                >
                  Resgatar Ingressos
                </Button>
                <p className="text-xs text-slate-500 mt-4">
                  Após o resgate, você poderá atribuir os ingressos aos participantes na sua conta
                </p>
              </div>
            )}

            {/* Terms */}
            <div className="text-xs text-slate-500 mt-8 border-t border-slate-200 pt-6">
              <p>Ingressos cortesia não podem ser transferidos ou vendidos.</p>
              <p className="mt-1">
                Válido apenas para o evento especificado. Sujeito aos termos e condições.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
