import { Event } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarDays, Clock, MapPin } from "lucide-react";
import { useLocation } from "wouter";

interface EventCardProps {
  event: Event;
}

export function EventCard({ event }: EventCardProps) {
  const [, setLocation] = useLocation();

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleViewDetails = () => {
    setLocation(`/events/${event.id}`);
  };

  return (
    <Card className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow duration-300">
      {event.image && (
        <img 
          src={event.image} 
          alt={event.name}
          className="w-full h-48 object-cover"
        />
      )}
      
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-primary-600 bg-primary-50 px-2 py-1 rounded-full">
            {event.city}
          </span>
          <span className="text-xs text-slate-500">
            {formatDate(event.start)}
          </span>
        </div>
        
        <h3 className="text-xl font-bold text-slate-900 mb-2 line-clamp-2">
          {event.name}
        </h3>
        
        {event.description && (
          <p className="text-slate-600 text-sm mb-4 line-clamp-2">
            {event.description}
          </p>
        )}
        
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center text-slate-500 text-sm">
            <MapPin className="w-4 h-4 mr-1" />
            <span className="truncate">{event.location}</span>
          </div>
          <div className="flex items-center text-slate-500 text-sm">
            <Clock className="w-4 h-4 mr-1" />
            <span>{formatTime(event.start)}</span>
          </div>
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            {event.min_price !== undefined && (
              <>
                <span className="text-lg font-bold text-primary-600">
                  R$ {Number(event.min_price).toFixed(2).replace(".", ",")}
                </span>
                <span className="text-sm text-slate-500 ml-1">a partir de</span>
              </>
            )}
          </div>
          <Button 
            onClick={handleViewDetails}
            className="bg-primary-600 text-white hover:bg-primary-700"
          >
            Ver Detalhes
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
