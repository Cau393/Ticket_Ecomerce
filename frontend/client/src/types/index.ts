export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  cpf?: string;
  phone?: string;
  is_active: boolean;
  created_at: string;
}

export interface Event {
  id: string;
  name: string;
  description?: string;
  location: string;
  city: string;
  start: string;
  end?: string;
  image?: string;
  is_active: boolean;
  created_at: string;
  ticket_classes?: TicketClass[];
  min_price?: number;
}

export interface TicketClass {
  id: string;
  event_id: string;
  name: string;
  description?: string;
  price: number;
  ticket_type: string;
  available_quantity?: number;
  created_at: string;
}

export interface Order {
  id: string;
  user_id?: string;
  total_amount: number;
  status: string;
  state: string;
  payment_method?: string;
  payment_id?: string;
  payment_data?: any;
  paid_at?: string;
  redemption_token?: string;
  created_at: string;
  items?: OrderItem[];
  tickets?: Ticket[];
}

export interface OrderItem {
  id: string;
  order_id: string;
  event_id: string;
  ticket_class_id: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
  created_at: string;
  event?: Event;
  ticket_class?: TicketClass;
}

export interface Ticket {
  id: string;
  order_id: string;
  order_item_id: string;
  holder_name?: string;
  holder_email?: string;
  created_at: string;
  order_item?: OrderItem;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  full_name: string;
  email: string;
  cpf: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  token: string;
}

export interface CartItem {
  ticket_class_id: string;
  quantity: number;
  holders: TicketHolder[];
}

export interface TicketHolder {
  holder_name: string;
  holder_email: string;
}

export interface CreateOrderData {
  items: CartItem[];
  billing_type: string;
}

export interface TicketAssignmentData {
  holder_name: string;
  holder_email: string;
}
