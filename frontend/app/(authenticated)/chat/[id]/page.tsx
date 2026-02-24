'use client';

import ChatInterface from '@/components/ChatInterface';
import { useParams } from 'next/navigation';

export default function ChatConversationPage() {
  const params = useParams();
  const conversationId = params.id as string;

  return <ChatInterface conversationId={conversationId} />;
}
