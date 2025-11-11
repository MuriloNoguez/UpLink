"""
Configuração e utilitários para o banco de dados PostgreSQL (Neon).
"""

import os
import logging
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2 import sql, Error
from psycopg2.extras import DictCursor
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador de conexão com PostgreSQL para o bot de tickets."""
    
    def __init__(self):
        """Inicializa o gerenciador com configurações de ambiente."""
        # URL de conexão do Neon (obtida do arquivo .env)
        self.database_url = os.getenv('DATABASE_URL') or "postgresql://neondb_owner:npg_FJcdz9Qp6w4HPGJUPBEPHIZhvBBcJhGz@ep-wild-recipe-a5m5vx6y.us-east-2.aws.neon.tech/neondb?sslmode=require"
        
        # Parse da URL para extrair componentes (caso precise)
        parsed = urlparse(self.database_url)
        self.config = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # Remove a barra inicial
            'user': parsed.username,
            'password': parsed.password,
        }
        
    def get_connection(self) -> Optional[psycopg2.extensions.connection]:
        """
        Estabelece e retorna uma conexão com o PostgreSQL.
        
        Returns:
            Conexão com PostgreSQL ou None em caso de erro
        """
        try:
            # Usar a URL diretamente é mais simples com PostgreSQL
            connection = psycopg2.connect(
                self.database_url,
                cursor_factory=DictCursor
            )
            return connection
            
        except Error as e:
            logger.error(f"Erro ao conectar com PostgreSQL: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Testa a conexão com o banco de dados.
        
        Returns:
            True se a conexão foi estabelecida com sucesso
        """
        try:
            connection = self.get_connection()
            if connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                connection.close()
                logger.info("Conexão com PostgreSQL testada com sucesso")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False
    
    def init_database(self) -> bool:
        """
        Inicializa o banco de dados e cria as tabelas necessárias.
        
        Returns:
            True se a inicialização foi bem-sucedida
        """
        try:
            connection = self.get_connection()
            if not connection:
                logger.error("Não foi possível conectar ao banco")
                return False
            
            logger.info("Conectado ao PostgreSQL com sucesso")
            
            with connection.cursor() as cursor:
                # Criar tabela de tickets
                create_table_query = """
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    user_name VARCHAR(255) NOT NULL,
                    channel_id BIGINT UNIQUE NOT NULL,
                    reason VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP NULL,
                    paused_at TIMESTAMP NULL,
                    paused_by VARCHAR(255) NULL
                );
                """
                
                cursor.execute(create_table_query)
                
                # Criar índices para melhor performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);",
                    "CREATE INDEX IF NOT EXISTS idx_tickets_channel_id ON tickets(channel_id);",
                    "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);",
                    "CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);"
                ]
                
                for index_query in indexes:
                    cursor.execute(index_query)
                
                connection.commit()
                logger.info("Tabela 'tickets' criada/verificada com sucesso")
                
            connection.close()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar banco: {e}")
            return False
    
    def create_ticket(self, user_id: int, user_name: str, channel_id: int, 
                     reason: str, description: str) -> Optional[int]:
        """
        Cria um novo ticket no banco de dados.
        
        Args:
            user_id: ID do Discord do usuário
            user_name: Nome do usuário
            channel_id: ID do canal criado
            reason: Motivo do ticket
            description: Descrição detalhada
            
        Returns:
            ID do ticket criado ou None em caso de erro
        """
        try:
            connection = self.get_connection()
            if not connection:
                return None
            
            with connection.cursor() as cursor:
                insert_query = """
                    INSERT INTO tickets (user_id, user_name, channel_id, reason, description)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                """
                
                cursor.execute(insert_query, (user_id, user_name, channel_id, reason, description))
                ticket_id = cursor.fetchone()['id']
                connection.commit()
                
                logger.info(f"Ticket {ticket_id} criado para usuário {user_name}")
                connection.close()
                return ticket_id
                
        except Exception as e:
            logger.error(f"Erro ao criar ticket: {e}")
            return None
    
    def get_ticket_by_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca um ticket pelo ID do canal.
        
        Args:
            channel_id: ID do canal no Discord
            
        Returns:
            Dados do ticket ou None se não encontrado
        """
        try:
            connection = self.get_connection()
            if not connection:
                return None
            
            with connection.cursor() as cursor:
                query = "SELECT * FROM tickets WHERE channel_id = %s ORDER BY id DESC LIMIT 1;"
                cursor.execute(query, (channel_id,))
                result = cursor.fetchone()
                
            connection.close()
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Erro ao buscar ticket por canal {channel_id}: {e}")
            return None
    
    def get_user_latest_ticket(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca o ticket mais recente de um usuário.
        
        Args:
            user_id: ID do usuário no Discord
            
        Returns:
            Dados do ticket mais recente ou None
        """
        try:
            connection = self.get_connection()
            if not connection:
                return None
            
            with connection.cursor() as cursor:
                query = """
                    SELECT * FROM tickets 
                    WHERE user_id = %s 
                    ORDER BY id DESC 
                    LIMIT 1;
                """
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                
            connection.close()
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Erro ao buscar último ticket do usuário {user_id}: {e}")
            return None
    
    def get_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Busca tickets de um usuário.
        
        Args:
            user_id: ID do usuário
            limit: Número máximo de tickets
            
        Returns:
            Lista de tickets do usuário
        """
        try:
            connection = self.get_connection()
            if not connection:
                return []
            
            with connection.cursor() as cursor:
                query = """
                    SELECT * FROM tickets 
                    WHERE user_id = %s 
                    ORDER BY id DESC 
                    LIMIT %s;
                """
                cursor.execute(query, (user_id, limit))
                results = cursor.fetchall()
                
            connection.close()
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Erro ao buscar tickets do usuário {user_id}: {e}")
            return []
    
    def close_ticket(self, channel_id: int) -> bool:
        """
        Fecha um ticket.
        
        Args:
            channel_id: ID do canal do ticket
            
        Returns:
            True se o ticket foi fechado com sucesso
        """
        try:
            connection = self.get_connection()
            if not connection:
                return False
            
            with connection.cursor() as cursor:
                query = """
                    UPDATE tickets 
                    SET status = 'closed', closed_at = CURRENT_TIMESTAMP
                    WHERE channel_id = %s AND status != 'closed';
                """
                cursor.execute(query, (channel_id,))
                connection.commit()
                
                # Verificar se alguma linha foi afetada
                success = cursor.rowcount > 0
                
            connection.close()
            logger.info(f"Ticket do canal {channel_id} {'fechado' if success else 'não encontrado/já fechado'}")
            return success
            
        except Exception as e:
            logger.error(f"Erro ao fechar ticket do canal {channel_id}: {e}")
            return False
    
    def reopen_ticket(self, channel_id: int, reason: str, description: str) -> Optional[int]:
        """
        Reabre um ticket existente com nova solicitação.
        
        Args:
            channel_id: ID do canal do ticket
            reason: Novo motivo
            description: Nova descrição
            
        Returns:
            ID do ticket reaberto ou None em caso de erro
        """
        try:
            connection = self.get_connection()
            if not connection:
                return None
            
            with connection.cursor() as cursor:
                # Buscar o ticket atual
                cursor.execute("SELECT id FROM tickets WHERE channel_id = %s ORDER BY id DESC LIMIT 1;", 
                             (channel_id,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                ticket_id = result['id']
                
                # Atualizar o ticket
                update_query = """
                    UPDATE tickets 
                    SET status = 'open', reason = %s, description = %s,
                        closed_at = NULL, paused_at = NULL, paused_by = NULL,
                        created_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """
                
                cursor.execute(update_query, (reason, description, ticket_id))
                connection.commit()
                
            connection.close()
            logger.info(f"Ticket {ticket_id} reaberto com novo motivo: {reason}")
            return ticket_id
            
        except Exception as e:
            logger.error(f"Erro ao reabrir ticket do canal {channel_id}: {e}")
            return None
    
    def pause_ticket(self, channel_id: int, paused_by: str) -> bool:
        """
        Pausa um ticket.
        
        Args:
            channel_id: ID do canal do ticket
            paused_by: Quem pausou o ticket
            
        Returns:
            True se pausado com sucesso
        """
        try:
            connection = self.get_connection()
            if not connection:
                return False
            
            with connection.cursor() as cursor:
                query = """
                    UPDATE tickets 
                    SET status = 'paused', paused_at = CURRENT_TIMESTAMP, paused_by = %s
                    WHERE channel_id = %s AND status = 'open';
                """
                cursor.execute(query, (paused_by, channel_id))
                connection.commit()
                
                success = cursor.rowcount > 0
                
            connection.close()
            return success
            
        except Exception as e:
            logger.error(f"Erro ao pausar ticket do canal {channel_id}: {e}")
            return False
    
    def unpause_ticket(self, channel_id: int) -> bool:
        """
        Despausa um ticket.
        
        Args:
            channel_id: ID do canal do ticket
            
        Returns:
            True se despausado com sucesso
        """
        try:
            connection = self.get_connection()
            if not connection:
                return False
            
            with connection.cursor() as cursor:
                query = """
                    UPDATE tickets 
                    SET status = 'open', paused_at = NULL, paused_by = NULL
                    WHERE channel_id = %s AND status = 'paused';
                """
                cursor.execute(query, (channel_id,))
                connection.commit()
                
                success = cursor.rowcount > 0
                
            connection.close()
            return success
            
        except Exception as e:
            logger.error(f"Erro ao despausar ticket do canal {channel_id}: {e}")
            return False
    
    def get_open_tickets(self) -> List[Dict[str, Any]]:
        """
        Busca todos os tickets abertos para fechamento automático.
        
        Returns:
            Lista de tickets abertos
        """
        try:
            connection = self.get_connection()
            if not connection:
                return []
            
            with connection.cursor() as cursor:
                query = "SELECT * FROM tickets WHERE status = 'open' ORDER BY created_at ASC;"
                cursor.execute(query)
                results = cursor.fetchall()
                
            connection.close()
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Erro ao buscar tickets abertos: {e}")
            return []
    
    def get_ticket_stats(self) -> Dict[str, int]:
        """
        Retorna estatísticas dos tickets.
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            connection = self.get_connection()
            if not connection:
                return {}
            
            with connection.cursor() as cursor:
                # Contar tickets por status
                cursor.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM tickets 
                    GROUP BY status;
                """)
                status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
                
                # Total de tickets
                cursor.execute("SELECT COUNT(*) as total FROM tickets;")
                total = cursor.fetchone()['total']
                
            connection.close()
            
            return {
                'total': total,
                'open': status_counts.get('open', 0),
                'closed': status_counts.get('closed', 0),
                'paused': status_counts.get('paused', 0)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            return {}