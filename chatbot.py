#!/usr/bin/env python3
"""
Chatbot RAG (Retrieval Augmented Generation)
Interroge la base de données Supabase et utilise OpenAI pour générer des réponses
"""

import os
import sys
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

from openai import OpenAI
from src.semantic_search import SemanticSearchEngine

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentChatbot:
    """
    Chatbot qui utilise RAG pour répondre aux questions
    basées sur les documents dans Supabase.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        search_limit: int = 5,
        search_threshold: float = 0.7
    ):
        """
        Initialise le chatbot.

        Args:
            model: Modèle OpenAI à utiliser (gpt-4o-mini, gpt-4, etc.)
            search_limit: Nombre de documents à récupérer pour le contexte
            search_threshold: Seuil de similarité pour la recherche
        """
        self.model = model
        self.search_limit = search_limit
        self.search_threshold = search_threshold

        # Initialiser OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY non trouvée dans .env")

        self.client = OpenAI(api_key=api_key)

        # Initialiser le moteur de recherche
        self.search_engine = SemanticSearchEngine()

        # Historique de conversation
        self.conversation_history: List[Dict[str, str]] = []

        logger.info(f"✅ Chatbot initialisé avec le modèle {model}")

    def search_documents(self, query: str) -> tuple[List[Dict], str]:
        """
        Recherche les documents pertinents.

        Args:
            query: Question de l'utilisateur

        Returns:
            Tuple (résultats de recherche, contexte formaté)
        """
        logger.info(f"🔍 Recherche de documents pour: {query}")

        results = self.search_engine.search(
            query=query,
            limit=self.search_limit,
            threshold=self.search_threshold
        )

        if not results:
            return [], "Aucun document pertinent trouvé dans la base de données."

        # Construire le contexte
        context_parts = []
        for result in results:
            file_name = result['file_name']
            content = result['content']
            similarity = result['similarity']

            context_parts.append(
                f"[Source: {file_name} - Pertinence: {similarity:.1%}]\n{content}"
            )

        context = "\n\n---\n\n".join(context_parts)

        logger.info(f"✅ {len(results)} documents trouvés")

        return results, context

    def generate_response(
        self,
        user_question: str,
        context: str,
        sources: List[Dict]
    ) -> str:
        """
        Génère une réponse avec OpenAI en utilisant le contexte.

        Args:
            user_question: Question de l'utilisateur
            context: Contexte des documents récupérés
            sources: Liste des sources (pour affichage)

        Returns:
            Réponse générée
        """
        # Construire le prompt système
        system_prompt = """Tu es un assistant intelligent qui répond aux questions en te basant sur des documents fournis.

INSTRUCTIONS:
1. Réponds UNIQUEMENT en te basant sur les informations contenues dans les documents fournis
2. Si la réponse n'est pas dans les documents, dis-le clairement
3. Cite toujours tes sources en mentionnant le nom du fichier
4. Sois précis et concis
5. Si plusieurs sources sont pertinentes, synthétise les informations
6. Réponds en français

CONTEXTE DES DOCUMENTS:
{context}
"""

        # Ajouter le message utilisateur
        messages = [
            {"role": "system", "content": system_prompt.format(context=context)}
        ]

        # Ajouter l'historique de conversation (limité aux 5 derniers échanges)
        for msg in self.conversation_history[-10:]:
            messages.append(msg)

        # Ajouter la question actuelle
        messages.append({"role": "user", "content": user_question})

        logger.info(f"🤖 Génération de la réponse avec {self.model}")

        try:
            # Appeler OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            answer = response.choices[0].message.content

            # Ajouter à l'historique
            self.conversation_history.append({"role": "user", "content": user_question})
            self.conversation_history.append({"role": "assistant", "content": answer})

            return answer

        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération: {e}")
            return f"Erreur lors de la génération de la réponse: {str(e)}"

    def ask(self, question: str, show_sources: bool = True) -> str:
        """
        Pose une question au chatbot.

        Args:
            question: Question de l'utilisateur
            show_sources: Afficher les sources utilisées

        Returns:
            Réponse complète avec sources
        """
        print(f"\n{'='*70}")
        print(f"❓ Question: {question}")
        print(f"{'='*70}\n")

        # 1. Rechercher les documents pertinents
        sources, context = self.search_documents(question)

        if not sources:
            response = "❌ Je n'ai trouvé aucun document pertinent pour répondre à cette question."
            print(response)
            return response

        # 2. Générer la réponse
        answer = self.generate_response(question, context, sources)

        # 3. Afficher la réponse
        print("🤖 Réponse:\n")
        print(answer)

        # 4. Afficher les sources si demandé
        if show_sources and sources:
            print(f"\n{'='*70}")
            print(f"📚 SOURCES UTILISÉES ({len(sources)} documents):")
            print(f"{'='*70}\n")

            for i, source in enumerate(sources, 1):
                print(f"{i}. {source['file_name']}")
                print(f"   Pertinence: {source['similarity']:.1%}")
                print(f"   Chunk: {source['chunk_index']}")
                print()

        return answer

    def reset_conversation(self):
        """Réinitialise l'historique de conversation."""
        self.conversation_history = []
        logger.info("🔄 Historique de conversation réinitialisé")

    def interactive_mode(self):
        """
        Mode interactif pour discuter avec le chatbot.
        """
        print("\n" + "="*70)
        print("🤖 CHATBOT RAG - MODE INTERACTIF")
        print("="*70)
        print("\nPosez vos questions sur les documents dans la base de données.")
        print("Commandes spéciales:")
        print("  - 'reset' : Réinitialiser la conversation")
        print("  - 'quit' ou 'exit' : Quitter")
        print("  - 'stats' : Afficher les statistiques")
        print("\n" + "="*70 + "\n")

        while True:
            try:
                # Lire la question
                question = input("\n💬 Votre question: ").strip()

                if not question:
                    continue

                # Commandes spéciales
                if question.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Au revoir !")
                    break

                if question.lower() == 'reset':
                    self.reset_conversation()
                    print("✅ Conversation réinitialisée")
                    continue

                if question.lower() == 'stats':
                    stats = self.search_engine.supabase_uploader.get_table_stats("documents")
                    print(f"\n📊 Statistiques:")
                    print(f"   Total documents: {stats.get('total_documents', 0)}")
                    continue

                # Poser la question
                self.ask(question, show_sources=True)

            except KeyboardInterrupt:
                print("\n\n👋 Au revoir !")
                break

            except Exception as e:
                logger.error(f"Erreur: {e}")
                print(f"\n❌ Erreur: {e}")


def main():
    """
    Point d'entrée principal du chatbot.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Chatbot RAG pour interroger vos documents"
    )

    parser.add_argument(
        "-q", "--question",
        type=str,
        help="Poser une question directement (mode non-interactif)"
    )

    parser.add_argument(
        "-m", "--model",
        type=str,
        default="gpt-4o-mini",
        help="Modèle OpenAI à utiliser (défaut: gpt-4o-mini)"
    )

    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=5,
        help="Nombre de documents à récupérer (défaut: 5)"
    )

    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.7,
        help="Seuil de similarité (défaut: 0.7)"
    )

    parser.add_argument(
        "--no-sources",
        action="store_true",
        help="Ne pas afficher les sources"
    )

    args = parser.parse_args()

    # Initialiser le chatbot
    try:
        chatbot = DocumentChatbot(
            model=args.model,
            search_limit=args.limit,
            search_threshold=args.threshold
        )

        # Mode direct (une question)
        if args.question:
            chatbot.ask(args.question, show_sources=not args.no_sources)

        # Mode interactif
        else:
            chatbot.interactive_mode()

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
