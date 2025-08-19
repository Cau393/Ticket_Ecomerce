import { apiGet } from "./api";
import { Event } from "@/types";

export const eventService = {
  async getEvents(params?: {
    search?: string;
    city?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }): Promise<Event[]> {
    const searchParams = new URLSearchParams();
    
    if (params?.search) searchParams.append("search", params.search);
    if (params?.city) searchParams.append("city", params.city);
    if (params?.category) searchParams.append("category", params.category);
    if (params?.limit) searchParams.append("limit", params.limit.toString());
    if (params?.offset) searchParams.append("offset", params.offset.toString());

    const queryString = searchParams.toString();
    const endpoint = queryString ? `/events/?${queryString}` : "/events/";
    
    return apiGet<Event[]>(endpoint);
  },

  async getEvent(id: string): Promise<Event> {
    return apiGet<Event>(`/events/${id}/`);
  }
};
