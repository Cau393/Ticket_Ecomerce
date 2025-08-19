import { apiPatch } from "./api";
import { Ticket, TicketAssignmentData } from "@/types";

export const ticketService = {
  async assignTicket(ticketId: string, data: TicketAssignmentData): Promise<Ticket> {
    return apiPatch<Ticket>(`/tickets/${ticketId}/assign/`, data);
  }
};
