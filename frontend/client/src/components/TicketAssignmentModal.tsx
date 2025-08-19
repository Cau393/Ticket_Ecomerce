import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ticketService } from "@/services/ticketService";
import { Ticket } from "@/types";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

const assignmentSchema = z.object({
  holder_name: z.string().min(1, "Nome é obrigatório"),
  holder_email: z.string().email("Email inválido"),
});

type AssignmentFormData = z.infer<typeof assignmentSchema>;

interface TicketAssignmentModalProps {
  ticket: Ticket | null;
  isOpen: boolean;
  onClose: () => void;
}

export function TicketAssignmentModal({ ticket, isOpen, onClose }: TicketAssignmentModalProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const form = useForm<AssignmentFormData>({
    resolver: zodResolver(assignmentSchema),
    defaultValues: {
      holder_name: "",
      holder_email: "",
    },
  });

  const assignMutation = useMutation({
    mutationFn: (data: AssignmentFormData) => {
      if (!ticket) throw new Error("No ticket selected");
      return ticketService.assignTicket(ticket.id, data);
    },
    onSuccess: () => {
      toast({
        title: "Ingresso atribuído com sucesso!",
        description: "O participante receberá o ingresso por email.",
      });
      queryClient.invalidateQueries({ queryKey: ["/api/orders"] });
      form.reset();
      onClose();
    },
    onError: (error) => {
      toast({
        title: "Erro ao atribuir ingresso",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const onSubmit = (data: AssignmentFormData) => {
    assignMutation.mutate(data);
  };

  const handleClose = () => {
    form.reset();
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Atribuir Ingresso</DialogTitle>
        </DialogHeader>

        {ticket && (
          <div className="mb-4 p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-600">Ingresso para:</p>
            <p className="font-medium text-slate-900">
              {ticket.order_item?.event?.name}
            </p>
            <p className="text-sm text-slate-600">
              {ticket.order_item?.ticket_class?.name} - R$ {ticket.order_item?.unit_price.toFixed(2).replace(".", ",")}
            </p>
          </div>
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="holder_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome do Participante *</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="Nome completo do participante" 
                      {...field} 
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="holder_email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>E-mail do Participante *</FormLabel>
                  <FormControl>
                    <Input 
                      type="email"
                      placeholder="email@exemplo.com" 
                      {...field} 
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex space-x-4 pt-4">
              <Button 
                type="button"
                variant="outline"
                onClick={handleClose}
                className="flex-1"
              >
                Cancelar
              </Button>
              <Button 
                type="submit"
                disabled={assignMutation.isPending}
                className="flex-1 bg-primary-600 hover:bg-primary-700"
              >
                {assignMutation.isPending ? "Atribuindo..." : "Atribuir Ingresso"}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
