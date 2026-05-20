const AUDIO_DURATIONS_MS: Record<string, number> = {
  "/audio/agent/agent_default_line_0.mp3": 12042,
  "/audio/agent/agent_default_line_1.mp3": 3787,
  "/audio/agent/agent_default_line_2.mp3": 2586,
  "/audio/agent/agent_default_line_3.mp3": 1802,
  "/audio/agent/agent_default_line_4.mp3": 2037,
  "/audio/agent/agent_default_line_5.mp3": 2768,
  "/audio/agent/agent_default_line_6.mp3": 3552,
  "/audio/suppliers/supplier_1_line_0.mp3": 6347,
  "/audio/suppliers/supplier_1_line_1.mp3": 8124,
  "/audio/suppliers/supplier_2_line_0.mp3": 8986,
  "/audio/suppliers/supplier_2_line_1.mp3": 10109,
  "/audio/suppliers/supplier_3_line_0.mp3": 9952,
  "/audio/suppliers/supplier_3_line_1.mp3": 9168,
  "/audio/suppliers/supplier_4_line_0.mp3": 7471,
  "/audio/suppliers/supplier_4_line_1.mp3": 6084,
  "/audio/suppliers/supplier_5_line_0.mp3": 7810,
  "/audio/suppliers/supplier_5_line_1.mp3": 8359,
};

export type ConversationLine = {
  speaker: "agent" | "supplier";
  audioUrl: string;
  text: string;
  durationMs: number;
};

export type SupplierConversation = {
  supplierId: number;
  lines: ConversationLine[];
};

function conversationLine(
  speaker: ConversationLine["speaker"],
  audioUrl: string,
  text: string,
): ConversationLine {
  return {
    speaker,
    audioUrl,
    text,
    durationMs: AUDIO_DURATIONS_MS[audioUrl] ?? 3000,
  };
}

export const conversations: SupplierConversation[] = [
  {
    supplierId: 1,
    lines: [
      conversationLine("agent", "/audio/agent/agent_default_line_0.mp3", "Hi, magandang umaga po. I'm calling on behalf of a client in Zambales. We need 20 bags of cement delivered to Iba by Friday. Budget is 8,000 pesos all-in. Pwede po ba kayong mag-quote?"),
      conversationLine("supplier", "/audio/suppliers/supplier_1_line_0.mp3", "Ay, Iba lang? Madali yan. Pwede ko i-deliver today, hindi pa Friday. Saan exact location?"),
      conversationLine("agent", "/audio/agent/agent_default_line_1.mp3", "Salamat po. Magkano po ang total, kasama ang delivery?"),
      conversationLine("supplier", "/audio/suppliers/supplier_1_line_1.mp3", "Sige, kasi local ka naman... PHP 7,500 na lang, kasama na delivery. Bayad on delivery, okay lang?"),
      conversationLine("agent", "/audio/agent/agent_default_line_2.mp3", "Perfect. Noted. Confirming shortly."),
    ],
  },
  {
    supplierId: 2,
    lines: [
      conversationLine("agent", "/audio/agent/agent_default_line_0.mp3", "Hi, magandang umaga po. I'm calling on behalf of a client in Zambales. We need 20 bags of cement delivered to Iba by Friday. Budget is 8,000 pesos all-in. Pwede po ba kayong mag-quote?"),
      conversationLine("supplier", "/audio/suppliers/supplier_2_line_0.mp3", "Twenty bags, Iba delivery. Let me check stock... yes, available. We can do Friday morning, before lunch."),
      conversationLine("agent", "/audio/agent/agent_default_line_1.mp3", "Salamat po. Magkano po ang total, kasama ang delivery?"),
      conversationLine("supplier", "/audio/suppliers/supplier_2_line_1.mp3", "PHP 7,800 delivered. Yan na ang best namin, includes fuel surcharge. Reliable kami, four years na kami nag-supply sa area."),
      conversationLine("agent", "/audio/agent/agent_default_line_2.mp3", "Perfect. Noted. Confirming shortly."),
    ],
  },
  {
    supplierId: 3,
    lines: [
      conversationLine("agent", "/audio/agent/agent_default_line_0.mp3", "Hi, magandang umaga po. I'm calling on behalf of a client in Zambales. We need 20 bags of cement delivered to Iba by Friday. Budget is 8,000 pesos all-in. Pwede po ba kayong mag-quote?"),
      conversationLine("supplier", "/audio/suppliers/supplier_3_line_0.mp3", "Good morning. Thank you for considering Subic Cement. For 20 bags delivered to Iba by Friday, our quote is PHP 8,200 all-in."),
      conversationLine("agent", "/audio/agent/agent_default_line_3.mp3", "Is there flexibility on the price?"),
      conversationLine("supplier", "/audio/suppliers/supplier_3_line_1.mp3", "PHP 8,200 is our best including delivery and standard handling. We invoice net-30 for repeat clients."),
      conversationLine("agent", "/audio/agent/agent_default_line_4.mp3", "Understood. Thank you for your time."),
    ],
  },
  {
    supplierId: 4,
    lines: [
      conversationLine("agent", "/audio/agent/agent_default_line_0.mp3", "Hi, magandang umaga po. I'm calling on behalf of a client in Zambales. We need 20 bags of cement delivered to Iba by Friday. Budget is 8,000 pesos all-in. Pwede po ba kayong mag-quote?"),
      conversationLine("supplier", "/audio/suppliers/supplier_4_line_0.mp3", "Cement? Ay, sir... wala kaming stock ngayon. Naubos kahapon. Restock next week pa."),
      conversationLine("agent", "/audio/agent/agent_default_line_5.mp3", "Walang available kahit konti?"),
      conversationLine("supplier", "/audio/suppliers/supplier_4_line_1.mp3", "Wala talaga, sir. Pasensya na. Try mo sa Zambales side, mas maraming supply doon ngayon."),
      conversationLine("agent", "/audio/agent/agent_default_line_6.mp3", "Sige, salamat sa info."),
    ],
  },
  {
    supplierId: 5,
    lines: [
      conversationLine("agent", "/audio/agent/agent_default_line_0.mp3", "Hi, magandang umaga po. I'm calling on behalf of a client in Zambales. We need 20 bags of cement delivered to Iba by Friday. Budget is 8,000 pesos all-in. Pwede po ba kayong mag-quote?"),
      conversationLine("supplier", "/audio/suppliers/supplier_5_line_0.mp3", "Iba delivery? Same town lang kami. Pwede today pa, before 5 PM. Twenty bags, tama?"),
      conversationLine("agent", "/audio/agent/agent_default_line_1.mp3", "Salamat po. Magkano po ang total, kasama ang delivery?"),
      conversationLine("supplier", "/audio/suppliers/supplier_5_line_1.mp3", "PHP 7,900, delivered. Kasama na yung pag-akyat sa storage ninyo. Cash or GCash, pareho lang."),
      conversationLine("agent", "/audio/agent/agent_default_line_2.mp3", "Perfect. Noted. Confirming shortly."),
    ],
  },
];
