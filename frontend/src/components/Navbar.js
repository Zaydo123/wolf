import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styled from 'styled-components';

const StyledNavbar = styled.nav`
  background-color: var(--background);
  border-bottom: 1px solid var(--primary);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 0 20px rgba(57, 255, 20, 0.5);
`;

const Logo = styled(Link)`
  font-family: var(--header-font);
  font-size: 1.5rem;
  color: var(--primary);
  text-shadow: 0 0 10px var(--primary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    text-shadow: 0 0 20px var(--primary);
  }
`;

const NavLinks = styled.div`
  display: flex;
  gap: 1.5rem;

  @media (max-width: 768px) {
    flex-direction: column;
    position: absolute;
    top: 4rem;
    right: 0;
    background-color: var(--background);
    padding: 1rem;
    border-left: 1px solid var(--primary);
    border-bottom: 1px solid var(--primary);
    box-shadow: 0 0 20px rgba(57, 255, 20, 0.5);
    z-index: 10;
    display: ${({ isOpen }) => (isOpen ? 'flex' : 'none')};
  }
`;

const NavItem = styled(Link)`
  color: var(--text);
  text-decoration: none;
  transition: all 0.3s ease;
  font-size: 1.1rem;

  &:hover, &.active {
    color: var(--primary);
    text-shadow: 0 0 10px var(--primary);
  }
`;

const LogoutButton = styled.button`
  background: none;
  border: none;
  color: var(--text);
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  font-family: var(--body-font);
  padding: 0;

  &:hover {
    color: var(--warning);
    text-shadow: 0 0 10px var(--warning);
  }
`;

const MobileMenuButton = styled.button`
  display: none;
  background: none;
  border: none;
  color: var(--primary);
  font-size: 1.5rem;
  cursor: pointer;
  
  @media (max-width: 768px) {
    display: block;
  }
`;

const Navbar = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = React.useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  const toggleMenu = () => {
    setMenuOpen(!menuOpen);
  };

  return (
    <StyledNavbar>
      <Logo to="/">
        <span>WOLF</span>
        <span className="blink">|</span>
      </Logo>

      <MobileMenuButton onClick={toggleMenu}>☰</MobileMenuButton>

      <NavLinks isOpen={menuOpen}>
        {isAuthenticated ? (
          <>
            <NavItem to="/" onClick={() => setMenuOpen(false)}>Dashboard</NavItem>
            <NavItem to="/portfolio" onClick={() => setMenuOpen(false)}>Portfolio</NavItem>
            <NavItem to="/calls" onClick={() => setMenuOpen(false)}>Call History</NavItem>
            <NavItem to="/settings" onClick={() => setMenuOpen(false)}>Settings</NavItem>
            <LogoutButton onClick={handleLogout}>Logout</LogoutButton>
          </>
        ) : (
          <>
            <NavItem to="/login" onClick={() => setMenuOpen(false)}>Login</NavItem>
            <NavItem to="/register" onClick={() => setMenuOpen(false)}>Register</NavItem>
          </>
        )}
      </NavLinks>
    </StyledNavbar>
  );
};

export default Navbar; 