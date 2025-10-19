import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Button } from './ui/button';

// Standard EU-14 allergen codes
const STANDARD_ALLERGENS = [
  'GLUTEN',
  'CRUSTACEANS',
  'MOLLUSCS',
  'EGGS',
  'FISH',
  'TREE_NUTS',
  'SOY',
  'DAIRY',
  'SESAME',
  'CELERY',
  'MUSTARD',
  'SULPHITES'
];

function AllergenSelector({ value = [], otherValue = [], onChange, onOtherChange, disabled = false }) {
  const { t } = useTranslation();
  const [otherInput, setOtherInput] = useState('');

  // Handle standard allergen checkbox toggle
  const handleToggle = (allergenCode) => {
    if (disabled) return;
    
    const newValue = value.includes(allergenCode)
      ? value.filter(code => code !== allergenCode)
      : [...value, allergenCode];
    
    onChange(newValue);
  };

  // Handle adding custom allergen
  const handleAddOther = () => {
    if (!otherInput.trim() || disabled) return;
    
    const trimmed = otherInput.trim();
    
    // Validation
    if (trimmed.length > 30) {
      alert(t('ingredients.error.allergenTooLong') || 'Allergen name too long (max 30 characters)');
      return;
    }
    
    if (otherValue.length >= 5) {
      alert(t('ingredients.error.tooManyCustomAllergens') || 'Maximum 5 custom allergens allowed');
      return;
    }
    
    // Check for duplicates (case-insensitive)
    const lowerTrimmed = trimmed.toLowerCase();
    
    // Check against standard allergens
    const isDuplicateStandard = STANDARD_ALLERGENS.some(code => 
      t(`allergens.${code}`).toLowerCase() === lowerTrimmed
    );
    
    if (isDuplicateStandard) {
      alert(t('ingredients.error.allergenAlreadyInList') || 'This allergen is already in the standard list');
      return;
    }
    
    // Check against other custom allergens
    const isDuplicateOther = otherValue.some(item => 
      item.toLowerCase() === lowerTrimmed
    );
    
    if (isDuplicateOther) {
      alert(t('ingredients.error.allergenAlreadyAdded') || 'This allergen has already been added');
      return;
    }
    
    onOtherChange([...otherValue, trimmed]);
    setOtherInput('');
  };

  // Handle removing custom allergen
  const handleRemoveOther = (index) => {
    if (disabled) return;
    onOtherChange(otherValue.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      {/* Standard Allergens - Checkbox Grid */}
      <div className="space-y-2">
        <Label>{t('ingredients.allergens') || 'Allergens'}</Label>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 p-4 border rounded-lg bg-gray-50">
          {STANDARD_ALLERGENS.map(code => (
            <label
              key={code}
              className={`flex items-center space-x-2 cursor-pointer ${disabled ? 'opacity-50' : 'hover:bg-gray-100'} p-2 rounded`}
            >
              <input
                type="checkbox"
                checked={value.includes(code)}
                onChange={() => handleToggle(code)}
                disabled={disabled}
                className="h-4 w-4"
                data-testid={`allergen-${code}`}
              />
              <span className="text-sm capitalize">
                {t(`allergens.${code}`)}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Other Allergens - Free Text with Chips */}
      <div className="space-y-2">
        <Label>{t('ingredients.otherAllergens') || 'Other Allergens'}</Label>
        
        {/* Display existing other allergens as chips */}
        {otherValue.length > 0 && (
          <div className="flex flex-wrap gap-2 p-3 border rounded-lg bg-gray-50">
            {otherValue.map((allergen, index) => (
              <div
                key={index}
                className="flex items-center gap-1 px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm"
                data-testid={`other-allergen-chip-${index}`}
              >
                <span>{allergen}</span>
                {!disabled && (
                  <button
                    type="button"
                    onClick={() => handleRemoveOther(index)}
                    className="hover:bg-orange-200 rounded-full p-0.5"
                    data-testid={`remove-other-allergen-${index}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Input to add new other allergen */}
        {!disabled && otherValue.length < 5 && (
          <div className="flex gap-2">
            <Input
              type="text"
              value={otherInput}
              onChange={(e) => setOtherInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddOther();
                }
              }}
              placeholder={t('ingredients.addOtherAllergen') || 'Add other allergen (max 30 chars)'}
              maxLength={30}
              className="flex-1"
              data-testid="other-allergen-input"
            />
            <Button
              type="button"
              onClick={handleAddOther}
              disabled={!otherInput.trim()}
              variant="outline"
              data-testid="add-other-allergen-button"
            >
              {t('common.add') || 'Add'}
            </Button>
          </div>
        )}
        
        {otherValue.length >= 5 && (
          <p className="text-sm text-gray-500">
            {t('ingredients.maxCustomAllergensReached') || 'Maximum 5 custom allergens reached'}
          </p>
        )}
      </div>
    </div>
  );
}

export default AllergenSelector;
