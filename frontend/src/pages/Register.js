import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styled from 'styled-components';

const RegisterContainer = styled.div`
  max-width: 400px;
  margin: 2rem auto;
  padding: 2rem;
  background-color: rgba(0, 0, 0, 0.8);
  border: 1px solid var(--primary);
  border-radius: 4px;
  box-shadow: 0 0 20px rgba(57, 255, 20, 0.3);
`;

const Title = styled.div`
  text-align: center;
  margin-bottom: 2rem;
  
  h2 {
    font-size: 24px;
    color: var(--text);
    margin-bottom: 10px;
  }
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  
  label {
    color: var(--text);
    font-size: 0.9rem;
  }
  
  input {
    padding: 0.75rem;
    background-color: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--primary);
    border-radius: 4px;
    color: var(--text);
    font-size: 1rem;
    
    &:focus {
      outline: none;
      box-shadow: 0 0 10px rgba(57, 255, 20, 0.3);
    }
  }
`;

const PasswordContainer = styled.div`
  position: relative;
  display: flex;
  align-items: stretch;
  
  input {
    width: 100%;
    padding-right: 60px;
    
    &:focus {
      outline: none;
      box-shadow: 0 0 10px rgba(57, 255, 20, 0.3);
      & + button {
        box-shadow: none;
      }
    }
  }

`;

const SubmitButton = styled.button`
  background-color: var(--primary);
  color: black;
  border: none;
  border-radius: 4px;
  padding: 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 1rem;
  
  &:hover {
    box-shadow: 0 0 15px var(--primary);
  }
  
  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
`;

const ErrorMessage = styled.div`
  color: var(--warning);
  text-align: center;
  margin-bottom: 1rem;
  padding: 0.5rem;
  border: 1px solid var(--warning);
  border-radius: 4px;
  background-color: rgba(255, 87, 51, 0.1);
`;

const Footer = styled.div`
  text-align: center;
  margin-top: 1.5rem;
  color: var(--text);
  
  a {
    color: var(--primary);
    text-decoration: none;
    margin-left: 0.5rem;
    transition: all 0.3s ease;
    
    &:hover {
      text-shadow: 0 0 10px var(--primary);
    }
  }
`;

const Register = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: '',
    phoneNumber: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (formData.password !== formData.confirmPassword) {
      return setError('Passwords do not match');
    }
    
    if (formData.password.length < 6) {
      return setError('Password must be at least 6 characters');
    }
    
    try {
      setLoading(true);
      await register(formData.email, formData.password, formData.name, formData.phoneNumber);
      navigate('/');
    } catch (err) {
      setError(err.message || 'An error occurred during registration');
      setLoading(false);
    }
  };

  const togglePasswordVisibility = (field) => {
    if (field === 'password') {
      setShowPassword(!showPassword);
    } else {
      setShowConfirmPassword(!showConfirmPassword);
    }
  };

  return (
    <RegisterContainer>
      <Title>
        <h2>Create Account</h2>
      </Title>
      
      {error && <ErrorMessage>{error}</ErrorMessage>}
      
      <Form onSubmit={handleSubmit}>
        <FormGroup>
          <label htmlFor="name">Full Name</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
          />
        </FormGroup>
        
        <FormGroup>
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
        </FormGroup>
        
        <FormGroup>
          <label htmlFor="phoneNumber">Phone Number (for calls)</label>
          <input
            type="tel"
            id="phoneNumber"
            name="phoneNumber"
            value={formData.phoneNumber}
            onChange={handleChange}
            required
          />
        </FormGroup>
        
        <FormGroup>
          <label htmlFor="password">Password</label>
          <PasswordContainer>
            <input
              type={showPassword ? "text" : "password"}
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
            />
            <button
              type="button"
              onClick={() => togglePasswordVisibility('password')}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </PasswordContainer>
        </FormGroup>
        
        <FormGroup>
          <label htmlFor="confirmPassword">Confirm Password</label>
          <PasswordContainer>
            <input
              type={showConfirmPassword ? "text" : "password"}
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
            />
            <button
              type="button"
              onClick={() => togglePasswordVisibility('confirm')}
            >
              {showConfirmPassword ? "Hide" : "Show"}
            </button>
          </PasswordContainer>
        </FormGroup>
        
        <SubmitButton 
          type="submit" 
          disabled={loading}
        >
          {loading ? 'Creating Account...' : 'Register'}
        </SubmitButton>
      </Form>
      
      <Footer>
        Already have an account? <Link to="/login">Login</Link>
      </Footer>
    </RegisterContainer>
  );
};

export default Register; 