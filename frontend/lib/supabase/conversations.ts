import { SupabaseClient } from '@supabase/supabase-js';

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  model_mode: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: any;
  classification?: any;
  model_mode?: string;
  created_at: string;
}

// --- Conversations ---

export async function getConversations(supabase: SupabaseClient): Promise<Conversation[]> {
  const { data, error } = await supabase
    .from('conversations')
    .select('*')
    .order('updated_at', { ascending: false });

  if (error) throw error;
  return data || [];
}

export async function createConversation(
  supabase: SupabaseClient,
  title: string = 'محادثة جديدة',
  modelMode: string = '2.1'
): Promise<Conversation> {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error('Not authenticated');

  const { data, error } = await supabase
    .from('conversations')
    .insert({ user_id: user.id, title, model_mode: modelMode })
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function updateConversationTitle(
  supabase: SupabaseClient,
  conversationId: string,
  title: string
): Promise<void> {
  const { error } = await supabase
    .from('conversations')
    .update({ title, updated_at: new Date().toISOString() })
    .eq('id', conversationId);

  if (error) throw error;
}

export async function deleteConversation(
  supabase: SupabaseClient,
  conversationId: string
): Promise<void> {
  const { error } = await supabase
    .from('conversations')
    .delete()
    .eq('id', conversationId);

  if (error) throw error;
}

// --- Messages ---

export async function getMessages(
  supabase: SupabaseClient,
  conversationId: string
): Promise<Message[]> {
  const { data, error } = await supabase
    .from('messages')
    .select('*')
    .eq('conversation_id', conversationId)
    .order('created_at', { ascending: true });

  if (error) throw error;
  return data || [];
}

export async function addMessage(
  supabase: SupabaseClient,
  conversationId: string,
  role: 'user' | 'assistant',
  content: string,
  extra?: { sources?: any; classification?: any; model_mode?: string }
): Promise<Message> {
  const { data, error } = await supabase
    .from('messages')
    .insert({
      conversation_id: conversationId,
      role,
      content,
      sources: extra?.sources || null,
      classification: extra?.classification || null,
      model_mode: extra?.model_mode || null,
    })
    .select()
    .single();

  if (error) throw error;

  // Update conversation timestamp
  await supabase
    .from('conversations')
    .update({ updated_at: new Date().toISOString() })
    .eq('id', conversationId);

  return data;
}
