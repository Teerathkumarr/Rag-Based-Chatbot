import streamlit as st
import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Assistant | Teerath Kumar",
    page_icon="🤖",
    layout="wide"
)

# Clean, professional CSS
st.markdown("""
<style>
    /* Main container */
    .main-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }
    
    /* Chat messages */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 14px 18px;
        border-radius: 20px 20px 4px 20px;
        margin: 12px 0;
        max-width: 85%;
        margin-left: auto;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    .ai-message {
        background: white;
        color: #1f2937;
        padding: 14px 18px;
        border-radius: 20px 20px 20px 4px;
        margin: 12px 0;
        max-width: 85%;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    /* Source badges */
    .source-badge {
        display: inline-block;
        background: #10b981;
        color: white;
        font-size: 0.75rem;
        padding: 2px 10px;
        border-radius: 12px;
        margin: 5px 5px 0 0;
        font-weight: 500;
    }
    
    /* Upload area */
    .upload-section {
        background: #f8fafc;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        border: 2px dashed #cbd5e1;
    }
    
    /* Hidden elements */
    .hidden {
        display: none;
    }
    
    /* Input area */
    .stChatInput {
        position: fixed;
        bottom: 20px;
        width: calc(100% - 40px);
        max-width: 860px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        border-top: 1px solid #e5e7eb;
        padding: 15px;
        box-shadow: 0 -4px 12px rgba(0,0,0,0.05);
        border-radius: 12px;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    default_state = {
        'messages': [],
        'documents': {},
        'tavily_key': os.getenv('TAVILY_API_KEY', ''),
        'gemini_key': os.getenv('GEMINI_API_KEY', ''),
        'chat_initialized': False,
        'thinking': False
    }
    
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

class ProfessionalChatbot:
    """Professional chatbot with automatic web search"""
    
    def __init__(self):
        self.tavily_key = st.session_state.tavily_key
        self.gemini_key = st.session_state.gemini_key
        
        # Initialize Gemini if key is available
        if self.gemini_key and self.gemini_key != "your_gemini_key_here":
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini_available = True
            except:
                self.gemini_available = False
        else:
            self.gemini_available = False
    
    def automatic_web_search(self, query):
        """Automatically search the web for information"""
        if not self.tavily_key or self.tavily_key == "your_tavily_key_here":
            return None
        
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "api_key": self.tavily_key,
                "query": query,
                "max_results": 3,
                "include_answer": True
            }
            
            response = requests.post(
                "https://api.tavily.com/search",
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception:
            return None
    
    def process_query(self, query):
        """Process user query with intelligent response generation"""
        
        # Check for creator question
        if any(keyword in query.lower() for keyword in ['who made you', 'who created you', 'who built you', 'teerath']):
            return self._get_creator_response(), 'ai'
        
        # Check if query is document-related
        if st.session_state.documents and self._is_document_query(query):
            doc_response = self._search_documents(query)
            if doc_response:
                return doc_response, 'document'
        
        # Always try web search first for factual/current information
        web_data = self.automatic_web_search(query)
        
        if web_data and 'results' in web_data:
            # Format web search results
            response = self._format_web_response(query, web_data)
            
            # Enhance with Gemini if available
            if self.gemini_available:
                enhanced = self._enhance_with_gemini(query, response)
                if enhanced:
                    return enhanced, 'web+ai'
            
            return response, 'web'
        
        # Use Gemini for general responses
        if self.gemini_available:
            try:
                model = genai.GenerativeModel('gemini-pro')
                ai_response = model.generate_content(
                    f"Please provide a helpful and accurate response to: {query}"
                )
                return ai_response.text, 'ai'
            except:
                pass
        
        # Fallback response
        return self._get_fallback_response(query), 'ai'
    
    def _is_document_query(self, query):
        """Check if query relates to uploaded documents"""
        query_lower = query.lower()
        doc_keywords = ['document', 'file', 'upload', 'content', 'text', 'pdf', 'txt']
        
        # Check for direct references to documents
        if any(keyword in query_lower for keyword in doc_keywords):
            return True
        
        # Check if query terms appear in documents
        for content in st.session_state.documents.values():
            for word in query_lower.split()[:3]:  # Check first 3 words
                if len(word) > 3 and word in content.lower():
                    return True
        
        return False
    
    def _search_documents(self, query):
        """Search in uploaded documents"""
        query_lower = query.lower()
        relevant_content = []
        
        for filename, content in st.session_state.documents.items():
            if query_lower in content.lower():
                # Extract relevant sentences
                sentences = content.split('.')
                for sentence in sentences:
                    if query_lower in sentence.lower():
                        relevant_content.append(sentence.strip())
                        if len(relevant_content) >= 2:
                            break
        
        if relevant_content:
            response = "Based on the uploaded documents:\n\n"
            for i, content in enumerate(relevant_content[:2], 1):
                response += f"{i}. {content}\n"
            
            # Enhance with Gemini if available
            if self.gemini_available:
                try:
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"Based on this document content: {' '.join(relevant_content[:2])}\n\nAnswer this question concisely: {query}"
                    ai_response = model.generate_content(prompt)
                    response = f"{ai_response.text}\n\n*Reference from uploaded documents*"
                except:
                    pass
            
            return response
        
        return None
    
    def _format_web_response(self, query, web_data):
        """Format web search results professionally"""
        response = ""
        
        # Include AI summary if available
        if 'answer' in web_data and web_data['answer']:
            response = f"{web_data['answer']}\n\n"
        
        # Include sources
        if 'results' in web_data and web_data['results']:
            response += "**Sources:**\n\n"
            for i, result in enumerate(web_data['results'][:2], 1):
                title = result.get('title', 'Source')
                url = result.get('url', '')
                snippet = result.get('content', '')[:120]
                
                if url:
                    response += f"{i}. [{title}]({url}) - {snippet}...\n"
                else:
                    response += f"{i}. {title} - {snippet}...\n"
        
        return response
    
    def _enhance_with_gemini(self, query, context):
        """Enhance response with Gemini AI"""
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"Question: {query}\n\nContext from web search: {context}\n\nProvide a clear, comprehensive answer based on this information."
            response = model.generate_content(prompt)
            return response.text
        except:
            return None
    
    def _get_creator_response(self):
        """Response for creator questions"""
        return "I was developed by **Teerath Kumar**. This AI assistant demonstrates advanced capabilities including real-time web search integration and document analysis for portfolio showcase purposes."
    
    def _get_fallback_response(self, query):
        """Professional fallback response"""
        return f"I'll help you with that. This response is based on general knowledge. For more specific or current information, please ensure your API keys are configured correctly in the environment variables."

def main():
    # Initialize chatbot
    chatbot = ProfessionalChatbot()

    # Professional header
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; margin-bottom: 2rem;">
        <h1 style="color: #2563eb; font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem;">
             Teerath's Chatbot
        </h1>
        <p style="color: #6b7280; font-size: 1rem; margin-top: 0;">
            Intelligent AI Assistant 
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Minimal sidebar - only file upload
    with st.sidebar:
        st.markdown("### 📁 Documents")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload text file",
            type=['txt'],
            label_visibility="collapsed",
            key="file_uploader"
        )
        
        if uploaded_file:
            content = uploaded_file.getvalue().decode('utf-8')
            st.session_state.documents[uploaded_file.name] = content
            st.success(f"✓ {uploaded_file.name}")
        
        # Show uploaded files
        if st.session_state.documents:
            st.markdown("---")
            st.markdown("**Uploaded:**")
            for filename in st.session_state.documents.keys():
                st.caption(f"• {filename}")
        
        st.markdown("---")
        
        # Clear chat button (minimal)
        if st.button("Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # Hidden status indicators
        with st.expander("ℹ️ Status", expanded=False):
            tavily_status = "✓ Configured" if st.session_state.tavily_key and st.session_state.tavily_key != "your_tavily_key_here" else "✗ Not set"
            gemini_status = "✓ Configured" if st.session_state.gemini_key and st.session_state.gemini_key != "your_gemini_key_here" else "✗ Not set"
            
            st.caption(f"Web Search: {tavily_status}")
            st.caption(f"AI Enhancement: {gemini_status}")
    
    # Main chat interface
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', 
                       unsafe_allow_html=True)
        else:
            # Show response with source badge if applicable
            content = message["content"]
            source_type = message.get("source", "ai")
            
            badge = ""
            if source_type == 'web':
                badge = '<span class="source-badge">Web</span>'
            elif source_type == 'web+ai':
                badge = '<span class="source-badge">AI+Web</span>'
            elif source_type == 'document':
                badge = '<span class="source-badge">Document</span>'
            
            st.markdown(f'<div class="ai-message">{content} {badge}</div>', 
                       unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Ask me anything...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get response
        with st.spinner(""):
            response, source_type = chatbot.process_query(user_input)
            
            # Add assistant message
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "source": source_type
            })
        
        st.rerun()

if __name__ == "__main__":
    main()