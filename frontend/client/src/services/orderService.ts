import { apiGet, apiPost } from "./api";
import { Order, CreateOrderData } from "@/types";

export const orderService = {
  async createOrder(data: CreateOrderData): Promise<Order> {
    return apiPost<Order>("/orders/", data);
  },

  async getOrders(): Promise<Order[]> {
    return apiGet<Order[]>("/orders/");
  },

  async getOrder(id: string): Promise<Order> {
    return apiGet<Order>(`/orders/${id}/`);
  },

  async checkPaymentStatus(orderId: string): Promise<Order> {
    return apiGet<Order>(`/orders/${orderId}/payment-status/`);
  }
};
