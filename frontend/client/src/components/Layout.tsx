import { useAuth } from "@/hooks/useAuth";
import { useLocation } from "wouter";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Menu, User, LogOut, Settings, ShoppingBag } from "lucide-react";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { isAuthenticated, user, logout } = useAuth();
  const [, setLocation] = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleNavigation = (path: string) => {
    setLocation(path);
    setMobileMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center">
              <button 
                onClick={() => handleNavigation("/")}
                className="flex-shrink-0"
              >
                <h1 className="text-2xl font-bold text-primary-600">CDPI Pass</h1>
              </button>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-8">
              <button 
                onClick={() => handleNavigation("/")}
                className="text-slate-700 hover:text-primary-600 px-3 py-2 text-sm font-medium transition-colors"
              >
                Eventos
              </button>
              <a href="#about" className="text-slate-700 hover:text-primary-600 px-3 py-2 text-sm font-medium transition-colors">
                Sobre
              </a>
              <a href="#contact" className="text-slate-700 hover:text-primary-600 px-3 py-2 text-sm font-medium transition-colors">
                Contato
              </a>
            </div>

            {/* Auth Buttons / User Menu */}
            <div className="flex items-center space-x-4">
              {!isAuthenticated ? (
                <div className="flex items-center space-x-3">
                  <Button
                    variant="ghost"
                    onClick={() => handleNavigation("/login")}
                    className="text-slate-700 hover:text-primary-600"
                  >
                    Entrar
                  </Button>
                  <Button
                    onClick={() => handleNavigation("/register")}
                    className="bg-primary-600 text-white hover:bg-primary-700"
                  >
                    Cadastrar
                  </Button>
                </div>
              ) : (
                <div className="flex items-center space-x-3">
                  <span className="text-sm text-slate-600 hidden sm:block">
                    {user?.full_name}
                  </span>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm" className="flex items-center">
                        <User className="h-5 w-5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-48">
                      <DropdownMenuItem onClick={() => handleNavigation("/account")}>
                        <User className="mr-2 h-4 w-4" />
                        Minha Conta
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleNavigation("/account")}>
                        <ShoppingBag className="mr-2 h-4 w-4" />
                        Meus Pedidos
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem>
                        <Settings className="mr-2 h-4 w-4" />
                        Configurações
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={logout}>
                        <LogOut className="mr-2 h-4 w-4" />
                        Sair
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              )}

              {/* Mobile menu button */}
              <div className="md:hidden">
                <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                  <SheetTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <Menu className="h-5 w-5" />
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="right" className="w-64">
                    <div className="flex flex-col space-y-4 mt-8">
                      <button 
                        onClick={() => handleNavigation("/")}
                        className="text-left px-3 py-2 text-slate-700 hover:text-primary-600"
                      >
                        Eventos
                      </button>
                      <a href="#about" className="text-left px-3 py-2 text-slate-700 hover:text-primary-600">
                        Sobre
                      </a>
                      <a href="#contact" className="text-left px-3 py-2 text-slate-700 hover:text-primary-600">
                        Contato
                      </a>
                      
                      {isAuthenticated && (
                        <>
                          <hr className="my-4" />
                          <button 
                            onClick={() => handleNavigation("/account")}
                            className="text-left px-3 py-2 text-slate-700 hover:text-primary-600"
                          >
                            Minha Conta
                          </button>
                          <button 
                            onClick={logout}
                            className="text-left px-3 py-2 text-slate-700 hover:text-primary-600"
                          >
                            Sair
                          </button>
                        </>
                      )}
                    </div>
                  </SheetContent>
                </Sheet>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      {children}

      {/* Footer */}
      <footer className="bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Company Info */}
            <div className="md:col-span-2">
              <h3 className="text-2xl font-bold mb-4">CDPI Pass</h3>
              <p className="text-slate-300 mb-4">
                A plataforma líder em venda de ingressos para eventos de tecnologia e inovação no Brasil.
              </p>
            </div>

            {/* Quick Links */}
            <div>
              <h4 className="text-lg font-semibold mb-4">Links Rápidos</h4>
              <ul className="space-y-2">
                <li>
                  <button 
                    onClick={() => handleNavigation("/")}
                    className="text-slate-300 hover:text-white transition-colors"
                  >
                    Eventos
                  </button>
                </li>
                <li>
                  <a href="#about" className="text-slate-300 hover:text-white transition-colors">
                    Como Funciona
                  </a>
                </li>
                <li>
                  <a href="#support" className="text-slate-300 hover:text-white transition-colors">
                    Suporte
                  </a>
                </li>
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h4 className="text-lg font-semibold mb-4">Legal</h4>
              <ul className="space-y-2">
                <li>
                  <a href="#terms" className="text-slate-300 hover:text-white transition-colors">
                    Termos de Uso
                  </a>
                </li>
                <li>
                  <a href="#privacy" className="text-slate-300 hover:text-white transition-colors">
                    Política de Privacidade
                  </a>
                </li>
                <li>
                  <a href="#contact" className="text-slate-300 hover:text-white transition-colors">
                    Contato
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-slate-800 mt-8 pt-8 text-center text-slate-400">
            <p>&copy; 2024 CDPI Pass. Todos os direitos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
